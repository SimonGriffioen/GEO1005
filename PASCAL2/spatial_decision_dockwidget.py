# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SpatialDecisionDockWidget
                                 A QGIS plugin
 This is a SDSS template for the GEO1005 course
                             -------------------
        begin                : 2015-11-02
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Jorge Gil, TU Delft
        email                : j.a.lopesgil@tudelft.nl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4 import QtGui, QtCore, uic
from qgis.core import *
from qgis.networkanalysis import *
from qgis.gui import *

# Initialize Qt resources from file resources.py
import resources

import processing
import os
import os.path
import random
import webbrowser
import csv

from . import utility_functions as uf

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'spatial_decision_dockwidget_base.ui'))


class SpatialDecisionDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = QtCore.pyqtSignal()
    #custom signals
    updateAttribute = QtCore.pyqtSignal(str)

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(SpatialDecisionDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # define globals
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.clickTool = QgsMapToolEmitPoint(self.canvas)
        self.panTool = QgsMapToolPan(self.canvas)
        # self.touchTool = QgsMapToolTouch(self.canvas)

        # set up GUI operation signals

        # canvas
        self.clickTool.canvasClicked.connect(self.handleMouseDown)

        #self.dlg = vector_selectbypointDialog()

        # GUI
        self.iface.projectRead.connect(self.setNodeAndNetwork)
        self.iface.newProjectCreated.connect(self.setNodeAndNetwork)
        self.iface.legendInterface().itemRemoved.connect(self.setNodeAndNetwork)
        self.iface.legendInterface().itemAdded.connect(self.setNodeAndNetwork)

        # data
        self.loadAmsterdamNoordButton.clicked.connect(self.loadDataAmsterdamNoord)

        # analysis
        self.scenarioCombo.currentIndexChanged.connect(self.scenarioChanged)
        self.sliderValue.textChanged.connect(self.sliderTextChanged)
        self.stationDistanceSlider.sliderMoved.connect(self.sliderMoved)
        self.stationDistanceSlider.valueChanged.connect(self.sliderValueChanged)
        self.stationDistanceButton.clicked.connect(self.buildNetwork)
        self.selectTransportCombo.activated.connect(self.setTransportMode)
        self.visibilityCheckBox.stateChanged.connect(self.showAll)
        self.addNodesButton.clicked.connect(self.addNode)
        self.createScenarioButton.clicked.connect(self.createScenario)
        self.graph = QgsGraph()
        self.tied_points = []


        self.scenarioPath = QgsProject.instance().homePath()
        self.scenarioCombo.clear()
        self.scenarioCombo.addItem('base')
        self.scenarioAttributes = {}

        # visualisation

        # reporting
        self.statistics1Table.itemClicked.connect(self.selectFeatureTable)
        self.statistics2Table.itemClicked.connect(self.selectFeatureTable)
        self.neighborhood = ('',False)

        # set current UI restrictions

        # add button icons
        self.bigiconButton.setIcon(QtGui.QIcon(':icons/pascal.png'))
        self.bigiconButton.clicked.connect(self.openinBrowser)

        # initialisation
        self.setNodeAndNetwork()

        #run simple tests

    def closeEvent(self, event):
        #disconnect interface signals
        try:
            self.iface.projectRead.disconnect(self.setNodeAndNetwork)
            self.iface.newProjectCreated.disconnect(self.setNodeAndNetwork)
            self.iface.legendInterface().itemRemoved.disconnect(self.setNodeAndNetwork)
            self.iface.legendInterface().itemAdded.disconnect(self.setNodeAndNetwork)
        except:
            pass

        self.closingPlugin.emit()
        event.accept()



#######
#   Data functions
#######
    def getScenarios(self):
        scenarios = [self.scenarioCombo.itemText(i) for i in range(self.scenarioCombo.count())]
        return scenarios

    def createScenario(self):
        # select the node layer
        vl = self.getBaseNodeLayer()
        #cl = self.iface.addVectorLayer( vl.source(), vl.name() + "_scenario", vl.providerType() )

        # create a path and filename for the new file
        path = QtGui.QFileDialog(self).getSaveFileName()
        list_path = path.split("/")[:-1]
        real_path =  '/'.join(list_path)
        self.scenarioPath = real_path
        scenarioName = path.split("/")[-1]
        self.scenarioCombo.addItem(scenarioName)
        index = self.scenarioCombo.count() - 1
        self.scenarioCombo.setCurrentIndex(index)

        filename = scenarioName + '_nodes'

        pathStyle = "%s/Styles/" % QgsProject.instance().homePath()
        # save the layer as shapefile
        if path:
            vlayer = uf.copyLayerToShapeFile(vl,real_path,filename)
            # add scenario to the project
            QgsMapLayerRegistry.instance().addMapLayer(vlayer, False)

            root = QgsProject.instance().layerTreeRoot()
            current_scenario = self.scenarioCombo.currentText()
            scenario_group = root.insertGroup(0, current_scenario)
            scenario_group.insertLayer(0, vlayer)

            layer = uf.getLegendLayerByName(self.iface, filename)
            layer.loadNamedStyle("{}styleNodes.qml".format(pathStyle))
            layer.triggerRepaint()
            self.iface.legendInterface().refreshLayerSymbology(layer)


    def setNodeAndNetwork(self):
        layers = uf.getLegendLayers(self.iface, 'all', 'all')
        network_text = self.selectNetworkCombo.currentText()
        if network_text == '':
            network_text = 'Road network'
        node_text = self.selectNodeCombo.currentText()
        if node_text == '':
            node_text = 'Nodes'
        self.selectNetworkCombo.clear()
        self.selectNodeCombo.clear()
        if layers:
            layer_names = uf.getLayersListNames(layers)
            self.selectNetworkCombo.addItems(layer_names)
            self.selectNodeCombo.addItems(layer_names)
            if layer_names.__contains__(network_text):
                index = self.selectNetworkCombo.findText(network_text)
                self.selectNetworkCombo.setCurrentIndex(index);
            if layer_names.__contains__(node_text):
                index = self.selectNodeCombo.findText(node_text)
                self.selectNodeCombo.setCurrentIndex(index);

        # current scenario
        scenarios = self.getScenarios()
        current_scenario = self.scenarioCombo.currentText()
        self.scenarioCombo.clear()
        index = 0
        for scenario in scenarios:
            root = QgsProject.instance().layerTreeRoot()
            scenario_group = root.findGroup(scenario)
            if scenario_group or scenario == 'base':
                self.scenarioCombo.addItem(scenario)
                if scenario == current_scenario:
                    self.scenarioCombo.setCurrentIndex(index)
                index = index + 1

    def showAll(self):
        checked = self.visibilityCheckBox.isChecked()
        if checked is True:
            vl = self.getCurrentNodeLayer()
            pathStyle = "%s/Styles/" % QgsProject.instance().homePath()
            vl.loadNamedStyle("{}styleNodes.qml".format(pathStyle))
            vl.triggerRepaint()
            self.iface.legendInterface().refreshLayerSymbology(vl)

            vl = self.getNetworkLayer()
            vl.loadNamedStyle("{}styleRoads.qml".format(pathStyle))
            vl.triggerRepaint()
            self.iface.legendInterface().refreshLayerSymbology(vl)
        elif checked is False:
            self.setTransportMode()


    def setTransportMode(self):
        if self.visibilityCheckBox.isChecked() is True:
            self.showAll()
        else:
            mode = self.selectTransportCombo.currentText()
            print mode
            vl = self.getCurrentNodeLayer()

            #root = QgsProject.instance().layerTreeRoot()
            pathStyle = "%s/Styles/" % QgsProject.instance().homePath()
            if mode == 'bus':
                # load only bus nodes
                vl.loadNamedStyle("{}styleBus.qml".format(pathStyle))
                vl.triggerRepaint()
                self.iface.legendInterface().refreshLayerSymbology(vl)
            elif mode == 'metro':
                # load nodes for specific transport mode
                vl.loadNamedStyle("{}styleMetro.qml".format(pathStyle))
                vl.triggerRepaint()
                self.iface.legendInterface().refreshLayerSymbology(vl)
            elif mode == 'ferry':
                # load nodes for specific transport mode
                vl.loadNamedStyle("{}styleFerry.qml".format(pathStyle))
                vl.triggerRepaint()
                self.iface.legendInterface().refreshLayerSymbology(vl)
            elif mode == 'tram':
                # load nodes for specific transport mode
                vl.loadNamedStyle("{}styleTram.qml".format(pathStyle))
                vl.triggerRepaint()
                self.iface.legendInterface().refreshLayerSymbology(vl)
            elif mode == 'rail':
                # load nodes for specific transport mode
                vl.loadNamedStyle("{}styleRail.qml".format(pathStyle))
                vl.triggerRepaint()
                self.iface.legendInterface().refreshLayerSymbology(vl)
            else:
                vl.loadNamedStyle("{}styleNodes.qml".format(pathStyle))
                vl.triggerRepaint()
                self.iface.legendInterface().refreshLayerSymbology(vl)

            # update road layer visibility
            vl = self.getNetworkLayer()
            if mode == 'bus':
                # load style roads for bus
                vl = self.getNetworkLayer()
                vl.loadNamedStyle("{}styleRoadBus.qml".format(pathStyle))
                vl.triggerRepaint()
                self.iface.legendInterface().refreshLayerSymbology(vl)
            elif mode == 'tram' or mode == 'metro' or mode == 'rail':
                # load style roads for specific transport mode
                vl = self.getNetworkLayer()
                vl.loadNamedStyle("{}styleRoadRails.qml".format(pathStyle))
                vl.triggerRepaint()
                self.iface.legendInterface().refreshLayerSymbology(vl)
            else:
                vl.loadNamedStyle("{}styleRoads.qml".format(pathStyle))
                vl.triggerRepaint()
                self.iface.legendInterface().refreshLayerSymbology(vl)



    def getNetworkLayer(self):
        layer_name = self.selectNetworkCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface,layer_name)
        return layer

    def getBaseNodeLayer(self):
        layer_name = self.selectNodeCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface,layer_name)
        return layer

    def getCurrentNodeLayer(self):
        layer_name = self.scenarioCombo.currentText() + '_nodes'
        layer = uf.getLegendLayerByName(self.iface,layer_name)

        if layer == None:
            layer_name = 'Nodes'
            layer = uf.getLegendLayerByName(self.iface,layer_name)
        return layer


    def loadDataAmsterdamNoord(self):
        try:
            data_path = os.path.join(os.path.dirname(__file__), 'sample_data','LayersPASCAL.qgs')
        except:
            self.createScenario()

        '''layer = QgsVectorLayer(data_path + '\Lines.shp', "Lines", "ogr")
        if not layer.isValid():
            print "Layer failed to load!"
        uf.loadTempLayer(layer)'''

        '''layer = self.iface.addVectorLayer(data_path + '\\Lines.shp', "Lines", "ogr")
        if not layer:
            print "Layer failed to load!"'''

        self.iface.addProject(data_path)

        # initialize layers
        self.baseAttributes()


    def baseAttributes(self):
        # get summary of the attribute
        layer = uf.getLegendLayerByName(self.iface, "base_gridStatistics")
        summary = []
        # only use the first attribute in the list
        for feature in layer.getFeatures():
            summary.append(feature)#, feature.attribute(attribute)))
        self.scenarioAttributes["base"] = summary
        # send this to the table
        self.clearTable()
        self.updateTable1()
        self.updateTable2()




    def run_mouse(self):
        self.canvas.setMapTool(self.clickTool)

#######
#    Analysis functions
#######
    def scenarioChanged(self):
        #grey out node stuff if current scenario is base
        if self.scenarioCombo.currentText() == 'base':
            self.selectTransportCombo.setEnabled(False)
            self.addNodesButton.setEnabled(False)
            self.stopNameEdit.setEnabled(False)
            self.visibilityCheckBox.setEnabled(False)
        else:
            self.selectTransportCombo.setEnabled(True)
            self.addNodesButton.setEnabled(True)
            self.stopNameEdit.setEnabled(True)
            self.visibilityCheckBox.setEnabled(True)

        #set visibility of layers
        root = QgsProject.instance().layerTreeRoot()
        current_scenario = self.scenarioCombo.currentText()
        AllItems = [self.scenarioCombo.itemText(i) for i in range(self.scenarioCombo.count())]

        for item in AllItems:
            scenario_group = root.findGroup(item)
            if scenario_group:
                if item == current_scenario:
                    scenario_group.setVisible(2)
                    scenario_layers = scenario_group.findLayers()
                    for layer in scenario_layers:
                        if layer.layerName() == current_scenario + '_gridStatistics':
                            layer.setVisible(0)
                else:
                    scenario_group.setVisible(0)


    def sliderTextChanged(self):
        value = self.sliderValue.text()
        try:
            value = int(value)
            self.stationDistanceSlider.setValue(int(value))
        except:
            print 'fill in a number'

    def sliderMoved(self, value):
        self.sliderValue.setText(str(value))

    def sliderValueChanged(self):
        current_scenario = self.scenarioCombo.currentText()
        filename = current_scenario + '_dist2station'
        raster_layer = uf.getLegendLayerByName(self.iface, filename)
        if raster_layer:
            self.styleStationDistance(raster_layer)

    def getNetwork(self):
        roads_layer = self.getSelectedLayer()
        if roads_layer:
            # see if there is an obstacles layer to subtract roads from the network
            obstacles_layer = uf.getLegendLayerByName(self.iface, "Obstacles")
            if obstacles_layer:
                # retrieve roads outside obstacles (inside = False)
                features = uf.getFeaturesByIntersection(roads_layer, obstacles_layer, False)
                # add these roads to a new temporary layer
                road_network = uf.createTempLayer('Temp_Network','LINESTRING',roads_layer.crs().postgisSrid(),[],[])
                road_network.dataProvider().addFeatures(features)
            else:
                road_network = roads_layer
            return road_network
        else:
            return


    def buildNetwork(self):
        self.network_layer = self.getNetworkLayer()

        if self.network_layer:
            # get the points to be used as origin and destination
            # in this case gets the centroid of the selected features

            nodeLayer = self.getCurrentNodeLayer()
            nodes = nodeLayer.getFeatures()
            source_points = []
            for node in nodes:
                source_points.append(node.geometry().asPoint())
            # build the graph including these points
            if len(source_points) > 1:
                self.graph, self.tied_points = uf.makeUndirectedGraph(self.network_layer, source_points)
            self.stationDistance()
        return

    def stationDistance(self):
        options = len(self.tied_points)
        if options > 0:
            # origin is given as an index in the tied_points list
            origin = random.randint(1,options-1)
            cutoff_distance = 100000
            service_area = uf.calculateStationDistance(self.graph, self.tied_points, cutoff_distance)
            # store the station distance results in temporary layer called "Service_Area"
            area_layer = uf.getLegendLayerByName(self.iface, "Service_Area")
            # create one if it doesn't exist
            if not area_layer:
                attribs = ['cost']
                types = [QtCore.QVariant.Double]
                area_layer = uf.createTempLayer('Service_Area','POINT',self.network_layer.crs().postgisSrid(), attribs, types)
                #uf.loadTempLayer(area_layer)
            # insert service area points
            geoms = []
            values = []
            for point in service_area:
                # each point is a tuple with geometry and cost
                geoms.append(point[0])
                # in the case of values, it expects a list of multiple values in each item - list of lists
                values.append([point[1]])
            uf.insertTempFeatures(area_layer, geoms, values)

            current_scenario = self.scenarioCombo.currentText()
            path = self.scenarioPath + '/' + current_scenario + '_dist2station'
            QgsVectorFileWriter.writeAsVectorFormat(area_layer,path+'.shp',str(area_layer.crs().postgisSrid()), None, "ESRI Shapefile")
            filename = path.split("/")[-1]
            service_area_layer = self.iface.addVectorLayer(path+'.shp', filename, "ogr")

            # interpolation
            processing.runalg('gdalogr:gridinvdist',service_area_layer,'cost',2,0,400,400,0,0,0,0,5,path+'.tif')

            # close intermediary layer
            QgsMapLayerRegistry.instance().removeMapLayer(service_area_layer.id())

            # delete old layer if present
            old_layer = uf.getLegendLayerByName(self.iface, current_scenario + '_dist2station')
            if old_layer:
                QgsMapLayerRegistry.instance().removeMapLayer(old_layer.id())

            fileName = path+'.tif'
            fileInfo = QtCore.QFileInfo(fileName)
            baseName = fileInfo.baseName()
            rasterLayer = QgsRasterLayer(fileName, baseName)
            QgsMapLayerRegistry.instance().addMapLayer(rasterLayer, False)

            root = QgsProject.instance().layerTreeRoot()
            current_scenario = self.scenarioCombo.currentText()
            scenario_group = root.findGroup(current_scenario)
            scenario_group.insertLayer(1, rasterLayer)



            # style raster layer
            self.styleStationDistance(rasterLayer)

            # Grid statistics
            self.rasterStatistics()


    def handleMouseDown(self, point, button):

        #print str(point.x()) + " , " +str(point.y()) )
        x_coor = point.x()
        y_coor = point.y()
        print x_coor, y_coor
        vl = self.getCurrentNodeLayer()
        pr = vl.dataProvider()
        vl.startEditing()

        # set new attributes
        stopname = self.stopNameEdit.text()
        mode = self.selectTransportCombo.currentText()

        # create new point for node
        fet = QgsFeature()
        fet.setGeometry( QgsGeometry.fromPoint(QgsPoint(x_coor,y_coor)))

        # add new attributes
        fet.setAttributes([stopname, mode])
        pr.addFeatures([fet])
        self.stopNameEdit.clear()

        # save changes
        vl.commitChanges()
        vl.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(vl)


        # set back to default settings
        self.selectTransportCombo.setCurrentIndex(0)
        self.setTransportMode()
        self.canvas.setMapTool(self.panTool)

    def addNode(self):
        node_added = self.run_mouse()


    # after adding features to layers needs a refresh (sometimes)
    def refreshCanvas(self, layer):
        if self.canvas.isCachingEnabled():
            layer.setCacheImage(None)
        else:
            self.canvas.refresh()

#######
#    Visualisation functions
#######

    def styleStationDistance(self, layer):
        break_value = self.sliderValue.text()

        fcn = QgsColorRampShader()
        fcn.setColorRampType(QgsColorRampShader.DISCRETE)
        lst = [ QgsColorRampShader.ColorRampItem(0, QtGui.QColor(255,255,255,0),'no data'), \
                QgsColorRampShader.ColorRampItem(int(break_value), QtGui.QColor(255,200,200,150),'<'+break_value), \
                QgsColorRampShader.ColorRampItem(100000, QtGui.QColor(150,20,20,150),'>'+break_value) ]
        fcn.setColorRampItemList(lst)
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(fcn)

        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader)
        layer.setRenderer(renderer)

        self.refreshCanvas(layer)

#######
#    Reporting functions
#######

    def rasterStatistics(self):
        # Get the layers that are needed (dist2station and neighborhoods)
        scenarioName = self.scenarioCombo.currentText()
        pathGrid = self.scenarioPath + '/' + scenarioName + '_dist2station.tif'
        print 'path grid =', pathGrid
        neigh = uf.getLegendLayerByName(self.iface,'Neighborhoods')
        # new layer for statistics
        layer_name = scenarioName + '_gridStatistics'
        pathStat = self.scenarioPath + '/' + layer_name +'.shp'
        filename = pathStat.split("/")[-1]

        # run SAGA processing algorithm
<<<<<<< HEAD
        processing.runalg("saga:gridstatisticsforpolygons",pathGrid, neigh, False, False, True, False, False, True, False, False, 0, pathStat)
        polyStat = QgsVectorLayer(pathStat, layer_name , 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(polyStat, False)
=======
        processing.runalg("saga:gridstatisticsforpolygons",pathGrid, test, False, False, True, False, False, True, False, False, 0, pathStat)
>>>>>>> origin/master

        # delete old layer if present
        old_layer = uf.getLegendLayerByName(self.iface, layer_name)
        if old_layer:
            QgsMapLayerRegistry.instance().removeMapLayer(old_layer.id())

        polyStat = QgsVectorLayer(pathStat, layer_name, 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(polyStat, False)
        root = QgsProject.instance().layerTreeRoot()
        current_scenario = self.scenarioCombo.currentText()
        scenario_group = root.findGroup(current_scenario)
        scenario_group.insertLayer(2, polyStat)
        legend = self.iface.legendInterface()
        legend.setLayerVisible(polyStat, False)

        layer = QgsMapCanvasLayer(polyStat)
        layer.setVisible(False)

        # get statistics in table
        self.extractAttributeSummary(layer_name, scenarioName)



    def extractAttributeSummary(self, layer_name, scenario):
        # get summary of the attribute
        layer = uf.getLegendLayerByName(self.iface,layer_name)
        summary = []
        # only use the first attribute in the list
        for feature in layer.getFeatures():
            summary.append(feature)#, feature.attribute(attribute)))

        self.scenarioAttributes[scenario] = summary
        # send this to the table
        self.clearTable()
        self.updateTable1()
        self.updateTable2()


    # table window functions
    def updateTable1(self):
        # Table 1 shows the maximum distance to a node for every neighborhood (index15)
        # takes a list of label / value pairs, can be tuples or lists. not dictionaries to control order
        headerLabels = ["Neigborhoods"]
        for scen in self.getScenarios():
            if scen in self.scenarioAttributes:
                headerLabels.append(scen)
        self.statistics1Table.setColumnCount(len(headerLabels))
        self.statistics1Table.setHorizontalHeaderLabels(headerLabels)
        self.statistics1Table.setRowCount(len(self.scenarioAttributes[headerLabels[1]]))

        # write neighborhoods in table
        if not self.scenarioAttributes.has_key('base'):
            self.baseAttributes()

        for i, item in enumerate(self.scenarioAttributes['base']):
            self.statistics1Table.setItem(i,0,QtGui.QTableWidgetItem(str(item[0])))

        # write maximum distance in table
        for n, scen in enumerate(headerLabels[1:]):
            value = self.scenarioAttributes[scen]
            for i, item in enumerate(value):
                self.statistics1Table.setItem(i,n+1,QtGui.QTableWidgetItem(str(int(item[14]))))




        """
        for n,list in enumerate(values):
            for i, item in enumerate(list):
                # i is the table row, items mus tbe added as QTableWidgetItems
                self.statistics1Table.setItem(i,0,QtGui.QTableWidgetItem(str(item[0])))
                self.statistics1Table.setItem(i,n+1,QtGui.QTableWidgetItem(str(item[15])))
        """
        self.statistics1Table.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.statistics1Table.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        self.statistics1Table.resizeRowsToContents()

    def updateTable2(self):
        # Table 2 shows the mean distance to a node for every neighborhood (index16)
        # takes a list of label / value pairs, can be tuples or lists. not dictionaries to control order
        headerLabels = ["Neigborhoods"]
        for scen in self.getScenarios():
            if scen in self.scenarioAttributes:
                headerLabels.append(scen)
        self.statistics2Table.setColumnCount(len(headerLabels))
        self.statistics2Table.setHorizontalHeaderLabels(headerLabels)
        self.statistics2Table.setRowCount(len(self.scenarioAttributes[headerLabels[1]]))

        # write neighborhoods in table
        for i, item in enumerate(self.scenarioAttributes['base']):
            self.statistics2Table.setItem(i,0,QtGui.QTableWidgetItem(str(item[0])))

        # write mean distance in table
        for n, scen in enumerate(headerLabels[1:]):
            value = self.scenarioAttributes[scen]
            for i, item in enumerate(value):
                self.statistics2Table.setItem(i,n+1,QtGui.QTableWidgetItem(str(int(item[15]))))
        self.statistics2Table.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.statistics2Table.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        self.statistics2Table.resizeRowsToContents()

        #self.selectFeatureTable()

    def clearTable(self):
        self.statistics1Table.clear()
        self.statistics2Table.clear()

    def openinBrowser(self):
<<<<<<< HEAD
        webbrowser.open('https://github.com/SimonGriffioen/pascal/wiki', new=2)

    def selectFeatureTable(self, item):
        if item.row() == self.neighborhood[0] and self.neighborhood[1] is True:
            for a in self.iface.attributesToolBar().actions():
                if a.objectName() == 'mActionDeselectAll':
                    a.trigger()
                    break
            self.neighborhood = (item.row(),False)
            return
        neighborhood = item.text()
        print item.row()
        print item.column()
        layer = uf.getLegendLayerByName(self.iface, "Neighborhoods")
        fids = [item.row()]
        request = QgsFeatureRequest().setFilterFids(fids)
        it = layer.getFeatures( request )
        ids = [i.id() for i in it]
        layer.setSelectedFeatures(ids)

        # zoom to feature
        self.canvas.zoomToSelected(layer)
        # deselect feature
        self.neighborhood = (item.row(),True)



=======
        webbrowser.open('http://github.com/SimonGriffioen/pascal/wiki/0.-Welcome', new=2)
>>>>>>> origin/master

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
import processing
# Initialize Qt resources from file resources.py
import resources


import os
import os.path
import random
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
        self.touchTool = QgsMapToolTouch(self.canvas)

        # set up GUI operation signals

        # canvas
        self.clickTool.canvasClicked.connect(self.handleMouseDown)

        #self.dlg = vector_selectbypointDialog()

        # data
        self.loadAmsterdamNoordButton.clicked.connect(self.loadDataAmsterdamNoord)

        # analysis
        self.sliderValue.textChanged.connect(self.sliderValueChanged)
        self.stationDistanceSlider.sliderMoved.connect(self.sliderMoved)
        self.stationDistanceSlider.sliderReleased.connect(self.sliderReleased)
        self.stationDistanceButton.clicked.connect(self.buildNetwork)
        self.selectTransportCombo.activated.connect(self.setTransportMode)
        self.visibilityCheckBox.stateChanged.connect(self.showAll)
        self.addNodesButton.clicked.connect(self.addNode)
        self.createScenarioButton.clicked.connect(self.createScenario)
        self.graph = QgsGraph()
        self.tied_points = []

        self.scenarioPath = QgsProject.instance().homePath()
        self.scenarios = ['base']
        self.scenarioCombo.addItems(self.scenarios)
        self.scenarioAttributes = {}



        # visualisation

        # reporting
        self.statisticsButton.clicked.connect(self.rasterStatistics)



        # set current UI restrictions

        # add button icons
        #self.medicButton.setIcon(QtGui.QIcon(':icons/medic_box.png'))

        # initialisation
        self.setNodeAndNetwork()

        #run simple tests



#######
#   Data functions
#######
    def createScenario(self):
        # select the node layer
        vl = self.getNodeLayer()
        #cl = self.iface.addVectorLayer( vl.source(), vl.name() + "_scenario", vl.providerType() )

        # create a path and filename for the new file
        path = QtGui.QFileDialog(self).getSaveFileName()
        list_path = path.split("/")[:-1]
        real_path =  '/'.join(list_path)
        self.scenarioPath = real_path
        scenarioName = path.split("/")[-1]
        self.scenarios.append(scenarioName)
        self.scenarioCombo.clear()
        self.scenarioCombo.addItems(self.scenarios)
        
        index = len(self.scenarios)-1
        self.scenarioCombo.setCurrentIndex(index)

        filename = scenarioName + '_nodes'

        pathStyle = "%s/Styles/" % QgsProject.instance().homePath()
        # save the layer as shapefile
        if path:
            vlayer = uf.copyLayerToShapeFile(vl,real_path,filename)
            # add scenario to the project
            QgsMapLayerRegistry.instance().addMapLayer(vlayer, False)

            root = QgsProject.instance().layerTreeRoot()
            root.insertLayer(1, vlayer)

            layer = uf.getLegendLayerByName(self.iface, filename)
            layer.loadNamedStyle("{}styleNodes.qml".format(pathStyle))
            layer.triggerRepaint()
            self.iface.legendInterface().refreshLayerSymbology(layer)


    def setNodeAndNetwork(self):
        layers = uf.getLegendLayers(self.iface, 'all', 'all')
        self.selectNetworkCombo.clear()
        self.selectNodeCombo.clear()
        if layers:
            layer_names = uf.getLayersListNames(layers)
            self.selectNetworkCombo.addItems(layer_names)
            self.selectNodeCombo.addItems(layer_names)

    def showAll(self):
        checked = self.visibilityCheckBox.isChecked()
        if checked is True:
            vl = self.getNodeLayer()
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
            vl = self.getNodeLayer()

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

    def getNodeLayer(self):
        layer_name = self.scenarioCombo.currentText() + '_nodes'
        layer = uf.getLegendLayerByName(self.iface,layer_name)

        if layer == None:
            layer_name = 'Nodes'
            layer = uf.getLegendLayerByName(self.iface,layer_name)
        
        return layer


    def loadDataAmsterdamNoord(self):
        try:
            data_path = 'C:\PluginDevelopment\pascal\sample_data\Layers QGIS - pascal\LayersPASCAL.qgs'
        except:
            data_path = '/Users/mj/Documents/Studie/GEO1005/pascal/sample_data/Layers QGIS - pascal/LayersPASCAL.qgs'

        '''layer = QgsVectorLayer(data_path + '\Lines.shp', "Lines", "ogr")
        if not layer.isValid():
            print "Layer failed to load!"
        uf.loadTempLayer(layer)'''

        '''layer = self.iface.addVectorLayer(data_path + '\\Lines.shp', "Lines", "ogr")
        if not layer:
            print "Layer failed to load!"'''

        self.iface.addProject(data_path)

    def run_mouse(self):
        self.canvas.setMapTool(self.clickTool)

#######
#    Analysis functions
#######
    def sliderValueChanged(self):
        value = self.sliderValue.text()
        try:
            value = int(value)
            self.stationDistanceSlider.setValue(int(value))
        except:
            print 'fill in a number'

    def sliderMoved(self, value):
        self.sliderValue.setText(str(value))

    def sliderReleased(self):
        scenarioName = self.scenarioCombo.currentText()
        filename = scenarioName + '_dist2station'
        raster_layer = uf.getLegendLayerByName(self.iface, filename)
        if raster_layer:
            print raster_layer
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

            nodeLayer = self.getNodeLayer()
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

            scenarioName = self.scenarioCombo.currentText()
            path = self.scenarioPath + '/' + scenarioName + '_dist2station'
            QgsVectorFileWriter.writeAsVectorFormat(area_layer,path+'.shp',str(area_layer.crs().postgisSrid()), None, "ESRI Shapefile")
            filename = path.split("/")[-1]
            service_area_layer = self.iface.addVectorLayer(path+'.shp', filename, "ogr")

            # interpolation
            processing.runalg('gdalogr:gridinvdist',service_area_layer,'cost',2,0,400,400,0,0,0,0,5,path+'.tif')

            fileName = path+'.tif'
            fileInfo = QtCore.QFileInfo(fileName)
            baseName = fileInfo.baseName()
            rasterLayer = QgsRasterLayer(fileName, baseName)
            QgsMapLayerRegistry.instance().addMapLayer(rasterLayer, False)
            root = QgsProject.instance().layerTreeRoot()
            root.insertLayer(5, rasterLayer)

            # close intermediary layer
            QgsMapLayerRegistry.instance().removeMapLayer(service_area_layer.id())

            # style raster layer
            self.styleStationDistance(rasterLayer)

            # Grid statistics
            self.rasterStatistics()


    def handleMouseDown(self, point, button):

        #print str(point.x()) + " , " +str(point.y()) )
        x_coor = point.x()
        y_coor = point.y()
        print x_coor, y_coor
        vl = self.getNodeLayer()
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
                QgsColorRampShader.ColorRampItem(int(break_value), QtGui.QColor(255,200,200),'<'+break_value), \
                QgsColorRampShader.ColorRampItem(100000, QtGui.QColor(150,20,20),'>'+break_value) ]
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
        # Get the layers that are needed (dist2station and neigborhoods)
        scenarioName = self.scenarioCombo.currentText()
        pathGrid = self.scenarioPath + '/' + scenarioName + '_dist2station.tif'
        pathPolygon = 'C:/Development/pascal/sample_data/Data QGIS - pascal/BuurtenStadsdeelNoord.shp'
        # new layer for statistics
        layer_name = scenarioName + '_gridStatistics'
        pathStat = self.scenarioPath + '/' + layer_name +'.shp'
        filename = pathStat.split("/")[-1]

        # run SAGA processing algorithm
        processing.runalg("saga:gridstatisticsforpolygons",pathGrid, pathPolygon, False, False, True, False, False, True, False, False, 0, pathStat)
        polyStat = QgsVectorLayer(pathStat, layer_name , 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(polyStat, False)
        root = QgsProject.instance().layerTreeRoot()
        root.insertLayer(5, polyStat)
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
        for scen in self.scenarios:
            if scen in self.scenarioAttributes:
                headerLabels.append(scen)
        self.statistics1Table.setColumnCount(len(headerLabels))
        self.statistics1Table.setHorizontalHeaderLabels(headerLabels)
        self.statistics1Table.setRowCount(len(self.scenarioAttributes[headerLabels[1]]))

        # write neighborhoods in table
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
        for scen in self.scenarios:
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

    def clearTable(self):
        self.statistics1Table.clear()
        self.statistics2Table.clear()

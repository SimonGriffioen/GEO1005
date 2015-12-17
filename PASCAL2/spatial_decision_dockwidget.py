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

        # set up GUI operation signals

        # canvas
        self.clickTool = QgsMapToolEmitPoint(self.canvas)
        self.clickTool.canvasClicked.connect(self.addElement)
        #self.dlg = vector_selectbypointDialog()

        # data
        self.iface.projectRead.connect(self.updateLayers)
        self.iface.newProjectCreated.connect(self.updateLayers)
        self.iface.legendInterface().itemRemoved.connect(self.updateLayers)
        self.iface.legendInterface().itemAdded.connect(self.updateLayers)
        self.loadAmsterdamNoordButton.clicked.connect(self.loadDataAmsterdamNoord)

        # analysis
        self.setNetworkButton2.clicked.connect(self.buildNetwork2)
        self.selectNetworkCombo.activated.connect(self.setNetworkLayer)
        self.selectNodeCombo.activated.connect(self.setNodeLayer)
        self.serviceAreaButton2.clicked.connect(self.calculateServiceArea2)
        self.addNodesButton.clicked.connect(self.addNode)
        self.createScenarioButton.clicked.connect(self.createScenario)
        self.graph = QgsGraph()
        self.tied_points = []

        # visualisation

        # reporting

        # set current UI restrictions

        # add button icons
        #self.medicButton.setIcon(QtGui.QIcon(':icons/medic_box.png'))

        # initialisation
        self.updateLayers()

        #run simple tests


    def closeEvent(self, event):
        print 'closeevent........'
        # disconnect interface signals
        try:
            self.iface.projectRead.disconnect(self.updateLayers)
            self.iface.newProjectCreated.disconnect(self.updateLayers)
            self.iface.legendInterface().itemRemoved.disconnect(self.updateLayers)
            self.iface.legendInterface().itemAdded.disconnect(self.updateLayers)
        except:
            pass

        self.closingPlugin.emit()
        event.accept()

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
        filename = path.split("/")[-1]

        # save the layer as shapefile
        if path:
            vlayer = uf.copyLayerToShapeFile(vl,real_path,filename)
            # add scenario to the project
            QgsMapLayerRegistry.instance().addMapLayer(vlayer)


    def updateLayers(self):

        print uf
        print 'updatelayers..................'
        print type(uf)

        #if type(uf) == None:
        layers = uf.getLegendLayers(self.iface, 'all', 'all')
        self.selectNetworkCombo.clear()
        self.selectNodeCombo.clear()
        if layers:
            layer_names = uf.getLayersListNames(layers)
            self.selectNetworkCombo.addItems(layer_names)
            self.selectNodeCombo.addItems(layer_names)

    def setNetworkLayer(self):
        pass

    def setNodeLayer(self):
        pass

    def getNetworkLayer(self):
        layer_name = self.selectNetworkCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface,layer_name)
        return layer

    def getNodeLayer(self):
        layer_name = self.selectNodeCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface,layer_name)
        return layer


    def loadDataAmsterdamNoord(self):

        data_path = 'C:\PluginDevelopment\pascal\sample_data\Layers QGIS - pascal\LayersPASCAL.qgs'

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

    def getNetwork(self):

        roads_layer = self.getSelectedLayer()

        print 'roads_layer'
        print roads_layer

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


    def buildNetwork2(self):
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
                print 'graph'
                print self.graph
                '''# the tied points are the new source_points on the graph
                if self.graph and self.tied_points:
                    text = "network is built for %s points" % len(self.tied_points)
                    self.insertReport(text)'''
        return

    def getServiceAreaCutoff(self):
        cutoff = self.serviceAreaCutoffEdit.text()
        if uf.isNumeric(cutoff):
            return uf.convertNumeric(cutoff)
        else:
            return 0

    def calculateServiceArea2(self):
        options = len(self.tied_points)
        if options > 0:
            # origin is given as an index in the tied_points list
            origin = random.randint(1,options-1)
            cutoff_distance = self.getServiceAreaCutoff()
            if cutoff_distance == 0:
                return
            service_area = uf.calculateServiceAreaAll(self.graph, self.tied_points, cutoff_distance)
            # store the service area results in temporary layer called "Service_Area"
            area_layer = uf.getLegendLayerByName(self.iface, "Service_Area")
            # create one if it doesn't exist
            if not area_layer:
                attribs = ['cost']
                types = [QtCore.QVariant.Double]
                area_layer = uf.createTempLayer('Service_Area','POINT',self.network_layer.crs().postgisSrid(), attribs, types)
                uf.loadTempLayer(area_layer)
            # insert service area points
            geoms = []
            values = []
            for point in service_area:
                # each point is a tuple with geometry and cost
                geoms.append(point[0])
                # in the case of values, it expects a list of multiple values in each item - list of lists
                values.append([point[1]])
            uf.insertTempFeatures(area_layer, geoms, values)
            self.refreshCanvas(area_layer)

    def addElement(self):
        self.iface.actionAddFeature().trigger()

    def addNode(self):
        # select scenario node layer
        vl = self.getNodeLayer()
        # edit the selected node layer
        vl.startEditing()
        # enable mouse on canvas
        node_added = self.run_mouse()
        print node_added

        if node_added:
            vl.commitChanges()
            vl.updateExtents()
            QgsMapLayerRegistry.instance().addMapLayer(vl)

        """
        fet = QgsFeature()
        fet.setGeometry(QgsGeometry.fromPoint())
        #pr.addFeatures()

        fet.setGeometry(QgsGeometry.fromPoint(QgsPoint(123871,488974)))
        pr.addFeatures([fet])


        print 'test1'
        nodeLayer.commitChanges()
        nodeLayer.updateExtents()
        print 'test2'
        QgsMapLayerRegistry.instance().addMapLayer(nodeLayer)

        nodes = nodeLayer.getFeatures()
        source_points = []
        for node in nodes:
            source_points.append(node.geometry().asPoint())
        # create a temporary layer
        node_layer = uf.getLegendLayerByName(self.iface, "Added_Nodes")
        if not node_layer:
        """

    # after adding features to layers needs a refresh (sometimes)
    def refreshCanvas(self, layer):
        if self.canvas.isCachingEnabled():
            layer.setCacheImage(None)
        else:
            self.canvas.refresh()

#######
#    Visualisation functions
#######

#######
#    Reporting functions
#######
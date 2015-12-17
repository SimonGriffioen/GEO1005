# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PASCALDockWidget
                                 A QGIS plugin
 Place A Station Connect A Location
                             -------------------
        begin                : 2015-12-04
        git sha              : $Format:%H$
        copyright            : (C) 2015 by PASCAL development group
        email                : info.marcjulien@gmail.com
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

import os

from PyQt4 import QtGui, uic
from PyQt4.QtCore import pyqtSignal
import resources

import os
import os.path
import random
import csv

from . import utility_functions as uf

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'PASCAL_dockwidget_base.ui'))


class PASCALDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()
    #custom signals
    updateAttribute = pyqtSignal(str)

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(PASCALDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # initialisation
        self.updateLayers()

        #Define globals
        self.iface = iface
        self.canvas = self.iface.mapCanvas()

        # set up GUI operation signals
        # project data
        self.iface.projectRead.connect(self.updateLayers)
        self.iface.newProjectCreated.connect(self.updateLayers)
        self.iface.legendInterface().itemRemoved.connect(self.updateLayers)
        self.iface.legendInterface().itemAdded.connect(self.updateLayers)

        #open and create buttons tab 1
        self.OpenButton.clicked.connect(self.openScenario)
        self.CreateButton.clicked.connect(self.createScenario)



    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()


    def openScenario(self,filename=""):
        scenario_open = False
        scenario_file = os.path.abspath(os.path.join(os.path.dirname( __file__ ), 'sample_data', 'Layers QGIS - pascal', 'LayersPASCAL.qgs'))
        # check if file exists
        if os.path.isfile(scenario_file):
            self.iface.addProject(scenario_file)
            scenario_open = True
        else:
            last_dir = uf.getLastDir("SDSS")
            new_file = QtGui.QFileDialog.getOpenFileName(self, "", last_dir, "(*.qgs)")
            if new_file:
                self.iface.addProject(new_file)
                scenario_open = True
        if scenario_open:
            self.updateLayers()


    def createScenario(self, filename):
        scenario_open = False
        scenario_file = os.path.join('/','sample_data','time_test.qgs')
        # check if file exists
        if os.path.isfile(scenario_file):
            self.iface.addProject(scenario_file)
            scenario_open = True
        else:
            last_dir = uf.getLastDir("SDSS")
            new_file = QtGui.QFileDialog.getOpenFileName(self, "", last_dir, "(*.qgs)")
            if new_file:
                self.iface.addProject(new_file)
                scenario_open = True
        if scenario_open:
            self.updateLayers()

    def saveScenario(self):
        self.iface.actionSaveProject()

    def updateLayers(self):
        layers = uf.getLegendLayers(self.iface, 'all', 'all')
        self.selectLayerCombo.clear()
        if layers:
            layer_names = uf.getLayersListNames(layers)
            self.selectLayerCombo.addItems(layer_names)
            self.setSelectedLayer()
        else:
            self.selectAttributeCombo.clear()
            self.clearChart()

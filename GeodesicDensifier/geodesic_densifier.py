# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeodesicDensifier
                                 A QGIS plugin
 Adds vertices to geometry along geodesic lines
                              -------------------
        begin                : 2017-10-06
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Jonah Sullivan
        email                : jonahsullivan79@gmail.com
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
try:
    from geographiclib.geodesic import Geodesic
except ImportError:
    import sys
    import inspect
    import os
    sys.path.append(os.path.dirname(os.path.abspath(inspect.getsourcefile(lambda: 0))))
    from geographiclib.geodesic import Geodesic
import math
from qgis.core import QgsFeature
from qgis.core import QgsGeometry
from qgis.core import QgsPoint
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from geodesic_densifier_dialog import GeodesicDensifierDialog
import os.path


class GeodesicDensifier:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'GeodesicDensifier_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Geodesic Densifier')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'GeodesicDensifier')
        self.toolbar.setObjectName(u'GeodesicDensifier')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('GeodesicDensifier', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        self.dlg = GeodesicDensifierDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/GeodesicDensifier/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Geodesic Densifier'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Geodesic Densifier'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            # Create a geographiclib Geodesic object
            # this is the GRS80 ellipsoid used for GDA94 EPSG:4283
            geod = Geodesic(6378137.0, 1 / 298.257222100882711243)

            def densifypoints(lat1, lon1, lat2, lon2, spacing):
                # create an empty list to hold points
                pline = []
                # create a geographiclib line object
                line_object = geod.InverseLine(lat1, lon1, lat2, lon2)
                # set the maximum separation between densified points
                ds = spacing
                # determine how many segments there will be
                n = int(math.ceil(line_object.s13 / ds)) + 1
                # adjust the spacing distance
                ds = line_object.s13 / n
                # this variable tracks how far along the line we are
                dist = 0.0
                # an extra segment is needed to add half of the modulo at the front of the line
                for i in range(n + 1):
                    g = line_object.Position(dist, Geodesic.STANDARD)
                    # add points to the line
                    pline.append(QgsPoint(g['lon2'], g['lat2']))
                    dist += ds
                return pline

            def densifypointssymmetrical(lat1, lon1, lat2, lon2, spacing):
                # create an empty list to hold points
                pline = []
                # create a geographiclib line object
                line_object = geod.InverseLine(lat1, lon1, lat2, lon2)
                # set the maximum separation between densified points
                ds = spacing
                # determine how many segments there will be
                n = int(math.ceil(line_object.s13 / ds))
                # this variable tracks how far along the line we are
                dist = 0.0
                # an extra segment is needed to add half of the modulo at the front of the line
                for i in range(n + 2):
                    if i == 0:
                        dist = 0
                    elif i == 1:
                        dist = (line_object.s13 % ds) / 2
                    elif i == n + 1:
                        dist = line_object.s13
                    else:
                        dist += ds
                    g = line_object.Position(dist, Geodesic.STANDARD)

                    # add points to the line
                    pline.append(QgsPoint(g['lon2'], g['lat2']))
                return pline

            # execute the function
            # Canberra to Darwin
            polylineList = densifypoints(-35.183, 149.1, -12.45, 130.8, 5000)

            # create and add to map canvas a memory layer
            lineLayer = self.iface.addVectorLayer("LineString", "Line Layer", "memory")

            # create a feature
            ft = QgsFeature()
            # get geometry from the list-of-QgsPoint
            # noinspection PyArgumentList,PyCallByClass
            polyline = QgsGeometry.fromPolyline(polylineList)
            # set geometry to the feature
            ft.setGeometry(polyline)
            # set data provider
            pr = lineLayer.dataProvider()
            # add feature to data provider
            pr.addFeatures([ft])

            # execute the function symmetrical
            # Canberra to Darwin
            polylineList = densifypointssymmetrical(-35.183, 149.1, -12.45, 130.8, 5000)

            # create and add to map canvas a memory layer
            lineLayer = self.iface.addVectorLayer("LineString", "Line Layer Symmetrical", "memory")

            # create a feature
            ft = QgsFeature()
            # get geometry from the list-of-QgsPoint
            # noinspection PyArgumentList,PyCallByClass
            polyline = QgsGeometry.fromPolyline(polylineList)
            # set geometry to the feature
            ft.setGeometry(polyline)
            # set data provider
            pr = lineLayer.dataProvider()
            # add feature to data provider
            pr.addFeatures([ft])
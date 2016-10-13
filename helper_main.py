#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Helper
                                 A QGIS plugin
 Plungin that helps you with your geospatial routine
                              -------------------
        begin                : 2016-09-28
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Innoter
        email                : lobanov@innoter.com
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
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from helper_main_dialog import HelperDialog
import os.path
# мои модули
# from ql_exporter import bka_ql_exporter
from ql_exporter import tab_template
import os
import shutil
import xml.etree.ElementTree as ET
from time import sleep
from string import Template
from PIL import Image
import zipfile
import contextlib
# import requests
import urllib
import tempfile
import ogr
from cStringIO import StringIO
# from temp_TH import th_ql_exporter


# задание стандартной директории
def lastUsedDir(type='in'):
    settings = QSettings("Innoter Helper", "helper")
    # можно 'C:\\' вместо ''
    if type == 'in':
        return settings.value("lastUsedInDir", str(""))
    elif type == 'out':
        return settings.value("lastUsedOutDir", str(""))


# обновление стандартной директории на последнюю использовавшуюся
def setLastUsedDir(lastDir, type='in'):
    path = QFileInfo(lastDir).absolutePath()
    settings = QSettings("Innoter Helper", "helper")
    if type == 'in':
        settings.setValue("lastUsedInDir", str(path))
    elif type == 'out':
        settings.setValue("lastUsedOutDir", str(path))


class Satellite:
    def __init__(self):
        self.satellite = None
        """"Задаём список доступных спутников"""
        self.sat_list = ["DEIMOS2", "BKA", "TH", ]
        # "TRIPLESAT",  "GF1", "ZY3", "GF2", "KAZEOSAT1", "KAZEOSAT2", "ALOS",
        #                  "PRISM",
        #                  "DG/WV-QB-IK-GE", "SPOT5", "SPOT67", "KOMPSAT2", "KOMPSAT3", ]

    def get_sat_list(self):
        return self.sat_list

    def set_curr_sat(self, new_satellite_value):
        self.satellite = new_satellite_value
        return self.satellite

    def get_curr_sat(self):
        return self.satellite


class Helper:
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
            'Helper_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = HelperDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Innoter Helper')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'Helper')
        self.toolbar.setObjectName(u'Helper')

        # мои переменные
        self.curr_filepath = None
        self.last_used_path = None
        self.out_dir = None
        self.satellite = Satellite()

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
        return QCoreApplication.translate('Helper', message)

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

        icon_path = ':/plugins/Helper/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Innoter Helper'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def populateGui(self):
        """Make the GUI live."""
        self.populateComboBox(self.dlg.SENSOR, self.satellite.get_sat_list(), u'Какой спутник ищем?', True)
        self.dlg.INPUT.setText(u'Где взять исходные файлы?')

    def runGui(self):
        self.dlg.SENSOR.currentIndexChanged.connect(lambda: self.satellite.set_curr_sat(self.dlg.SENSOR.currentText()))
        self.dlg.INPUTbrowse.clicked.connect(
            lambda: self.select_input_file(sensor=self.satellite.get_curr_sat()))
        self.dlg.OUTPUTbrowse.clicked.connect(
            lambda: self.select_output_dir())
        self.dlg.START.clicked.connect(lambda: self.start_processing())

    def upd_progress(self, value):
        self.dlg.progressBar.setValue(value)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Innoter Helper'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run(self):
        """Run method that performs all the real work"""
        self.populateGui()
        self.runGui()
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def populateComboBox(self, combo, list, predef, sort):
        # procedure to fill specified combobox with provided list
        combo.blockSignals(True)
        combo.clear()
        model = QStandardItemModel(combo)
        predefInList = None
        for elem in list:
            try:
                item = QStandardItem(unicode(elem))
            except TypeError:
                item = QStandardItem(str(elem))
            model.appendRow(item)
            if elem == predef:
                predefInList = elem
        if sort:
            model.sort(0)
        combo.setModel(model)
        if predef != "":
            if predefInList:
                combo.setCurrentIndex(combo.findText(predefInList))
            else:
                combo.insertItem(0, predef)
                combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def select_input_file(self, sensor):
        if sensor == 'BKA':
            file_format = u' БКА (*.kml *.kmz *.KML *.KMZ)'
        elif sensor == 'DEIMOS2':
            file_format = u' Deimos-2 (*.zip *.ZIP)'
        elif sensor == 'TH':
            file_format = u' TH (*.zip *.ZIP)'
        else:
            file_format = u'??? (Сенсор не задан)'
        self.curr_filepath = QFileDialog.getOpenFileName(
                self.dlg, u"Укажите файл контура ", lastUsedDir(), file_format)
        if self.curr_filepath != '':
            self.dlg.INPUT.setText(self.curr_filepath)
            setLastUsedDir(os.path.dirname(self.curr_filepath))
            self.out_dir = os.path.dirname(self.curr_filepath)
            self.dlg.OUTPUT.setText(self.out_dir)

        else:
            self.dlg.INPUT.setText(u'Где взять исходные файлы?')

    # TODO сделать select_..._ функцией по типу populate_combo
    def select_output_dir(self):
        self.out_dir = QFileDialog.getExistingDirectory(
            self.dlg, u"Укажите файл контура ", lastUsedDir(type='out'))
        if self.out_dir != '':
            self.dlg.OUTPUT.setText(self.out_dir)
            setLastUsedDir(self.out_dir, type='out')

    def start_processing(self):
        sensor = self.satellite.get_curr_sat()
        source_file = self.curr_filepath
        dst_path = self.dlg.OUTPUT.text()
        if sensor == 'BKA':
            self.bka_ql_exporter(source_file, dst_path)
        elif sensor == 'DEIMOS2':
            self.deimos_ql_exporter(source_file, dst_path)
        elif sensor == 'TH':
            self.th_ql_exporter(source_file, dst_path)

    # TODO убрать это в импортируемый модуль (для этого нужно разобраться, как ему подключиться к iface)
    def bka_ql_exporter(self, source_file, dst_dirpath):
        src_file = source_file
        dst_dir_name = 'QuickLooks'
        dst_dir_path = os.path.join(dst_dirpath, dst_dir_name)

        if not os.path.exists(dst_dir_path):
            os.makedirs(dst_dir_path)

        # парсим kml
        if src_file.endswith(('.kml', '.KML')):
            tree = ET.parse(src_file)
        else:
            # src_file.endswith(('.kmz', '.KMZ'))
            with zipfile.ZipFile(src_file) as kmz:
                for filename in kmz.namelist():
                    if filename.endswith(('.kml', '.KML')):
                        # парсим kml
                        # TODO проверить, закрывается ли kml просле окончания with
                        with kmz.open(filename, 'r') as kml:
                            tree = ET.parse(kml)
                        break
        root = tree.getroot()

        # ищем в kml все записи, описывающие квиклук
        ql_kml_list = root.findall(".//GroundOverlay")

        # print(len(q))
        counter = 0
        for q in range(len(ql_kml_list)):
            ql_filename = ql_kml_list[q].find(".//href").text
            standard_ql_name = ql_filename[:13]
            # стандартизируем имя и копируем квиклук в целевую директорию, где измеряем его пикс. ширину и высоту
            ql_dst_path = os.path.join(dst_dir_path, standard_ql_name + '.jpg')
            if src_file.endswith(('.kml', '.KML')):
                shutil.copy(os.path.join(os.path.dirname(src_file), ql_filename), ql_dst_path)
            else:
                with zipfile.ZipFile(src_file) as kmz:
                    with kmz.open(ql_filename) as zipped_ql, open(ql_dst_path, 'wb') as f:
                        shutil.copyfileobj(zipped_ql, f)
            ql_image_obj = Image.open(ql_dst_path)
            ql_width, ql_height = ql_image_obj.size[0], ql_image_obj.size[1]
            del ql_image_obj
            coords_str = ql_kml_list[q].find(".//coordinates").text
            # преобразуем строку с координатами углов в список и разбиваем по 4 точкам
            coords_lst = coords_str.split('\n')
            c1, c2, c3, c4 = coords_lst[3], coords_lst[0], coords_lst[1], coords_lst[2]
            text_content = tab_template('bka', standard_ql_name, c1, c2, c3, c4, ql_height, ql_width)
            with open(os.path.join(dst_dir_path, standard_ql_name + '.tab'), 'w') as f:
                f.write(text_content.strip())
            counter += 1
            self.dlg.progressBar.setValue((100*counter/len(ql_kml_list)))
        QMessageBox.information(None, 'Result', u'Готово!\nСоздано квиклуков: ' + str(len(ql_kml_list)))
        if self.dlg.browse_on_complete.isChecked():
            os.startfile(dst_dir_path)
        else:
            pass

    def deimos_ql_exporter(self, source_file, dst_dirpath):
        @contextlib.contextmanager
        def make_temp_directory():
            temp_dir = tempfile.mkdtemp()
            try:
                yield temp_dir
            finally:
                shutil.rmtree(temp_dir)
        # TODO следующий блок дублируется в БКА.
        dst_dir_name = 'QuickLooks'
        dst_dir_path = os.path.join(dst_dirpath, dst_dir_name)
        if not os.path.exists(dst_dir_path):
            os.makedirs(dst_dir_path)
        with make_temp_directory() as tmpdir:
            with zipfile.ZipFile(source_file, 'r') as zfile:
                zfile.extractall(tmpdir)
                ql_list = [f for dp, dn, filenames in os.walk(tmpdir) for f in filenames if f.endswith(('.kmz', '.KMZ'))
                           and f[-7:-4] != 'ALL']
            # QMessageBox.information(None, 'Result', str(len(ql_list)))
            for dirpath, dirnames, filenames in os.walk(tmpdir):
                counter = 0
                for filename in filenames:
                    if filename.endswith(('.kmz', '.KMZ')) and filename[-7:-4] != 'ALL':
                        in_file = os.path.join(dirpath, filename)
                        with zipfile.ZipFile(in_file, 'r') as kmz:
                            with kmz.open('doc.kml', 'r') as kml:
                                kml_tree = ET.parse(kml)
                        root = kml_tree.getroot()
                        ql_kml_list = root.findall(".//{http://earth.google.com/kml/2.1}GroundOverlay")
                        for q in range(len(ql_kml_list)):
                            ql_filename = ql_kml_list[q].find(".//{http://earth.google.com/kml/2.1}name").text
                            standard_ql_name = ql_filename[11:]
                            ql_dst_path = os.path.join(dst_dir_path, standard_ql_name + '.jpg')
                            ql_url = ql_kml_list[q].find(".//{http://earth.google.com/kml/2.1}href").text
                            content = StringIO(urllib.urlopen(ql_url).read())
                            i = Image.open(content)
                            i.save(ql_dst_path, format='JPEG', quality=80)
                            del i
                            # response = requests.get(ql_url)
                            # if response.status_code == 200:
                            #     i = Image.open(StringIO(response.content))
                            #     i.save(ql_dst_path, format='JPEG', quality=80)
                            # else:
                            #     # TODO выводить ошибку "не удалось скачать квиклук с сервера DEIMOS
                            #     raise IOError
                            ql_image_obj = Image.open(ql_dst_path)
                            ql_width, ql_height = ql_image_obj.size[0], ql_image_obj.size[1]
                            del ql_image_obj
                            north = ql_kml_list[q].find(".//{http://earth.google.com/kml/2.1}north").text
                            south = ql_kml_list[q].find(".//{http://earth.google.com/kml/2.1}south").text
                            east = ql_kml_list[q].find(".//{http://earth.google.com/kml/2.1}east").text
                            west = ql_kml_list[q].find(".//{http://earth.google.com/kml/2.1}west").text
                            c1, c2, c3, c4 = ','.join((str(west), str(north))), ','.join((str(east), str(north))), \
                                             ','.join((str(east), str(south))), ','.join((str(west), str(south)))
                            text_content = tab_template('deimos', standard_ql_name, c1, c2, c3, c4, ql_height, ql_width)
                            with open(os.path.join(dst_dir_path, standard_ql_name + '.tab'), 'w') as f:
                                f.write(text_content.strip())
                            counter += 1
                            self.dlg.progressBar.setValue((100 * counter / len(ql_list)))
            QMessageBox.information(None, 'Result',
                                    u'Готово!\nСоздано квиклуков: ' + str(len(ql_list)))
            if self.dlg.browse_on_complete.isChecked():
                os.startfile(dst_dir_path)

    def th_ql_exporter(self, source_file, dst_dirpath):
        @contextlib.contextmanager
        def make_temp_directory():
            temp_dir = tempfile.mkdtemp()
            try:
                yield temp_dir
            finally:
                shutil.rmtree(temp_dir)

        src_file = source_file
        dst_dir_name = 'QuickLooks'
        dst_dir_path = os.path.join(dst_dirpath, dst_dir_name)
        if not os.path.exists(dst_dir_path):
            os.makedirs(dst_dir_path)

        def get_ql_path(qiucklook_name):
            for ql_path in ql_path_list:
                if qiucklook_name == ql_path.split('.')[-2][-46:-4]:
                    return ql_path

        with make_temp_directory() as tmpdir:
            with zipfile.ZipFile(src_file, 'r') as zfile:
                zfile.extractall(tmpdir)

            ql_path_list = []
            src_shape = ''
            for dirpath, dirnames, filenames in os.walk(tmpdir):
                for filename in filenames:
                    if filename.endswith(('.jpg', '.JPG')):
                        ql_path_list.append(os.path.join(tmpdir, filename))
                    if filename.endswith(('.shp', '.SHP')):
                        src_shape = os.path.join(tmpdir, filename)
                        continue

            driver = ogr.GetDriverByName('ESRI Shapefile')
            dataSource = driver.Open(src_shape, 0)
            layer = dataSource.GetLayer(0)
            ql_list = layer.GetFeatureCount()
            counter = 0
            for img_contour in layer:
                ql_name = img_contour.GetField('ImgIdDgp')
                geometry = img_contour.GetGeometryRef()
                ring = geometry.GetGeometryRef(0)
                coord_list = ['', '', '', '']
                list_counter = 0
                for point_id in range(ring.GetPointCount() - 1):
                    lon, lat, z = ring.GetPoint(point_id)
                    coord_list[list_counter] = str(','.join((str(lon), str(lat))))
                    list_counter += 1
                ql_path = get_ql_path(ql_name)
                ql_dst_path = os.path.join(dst_dir_path, ql_name + '_Bro' + '.jpg')
                shutil.copy(ql_path, ql_dst_path)
                ql_image_obj = Image.open(ql_path)
                ql_width, ql_height = ql_image_obj.size[0], ql_image_obj.size[1]
                del ql_image_obj
                text_content = tab_template(
                    'TH', ql_name + '_Bro', coord_list[0], coord_list[3], coord_list[2], coord_list[1], ql_height,
                    ql_width)
                with open(os.path.join(dst_dir_path, ql_name + '_Bro' + '.tab'), 'w') as f:
                    f.write(text_content.strip())
                    counter += 1
                    self.dlg.progressBar.setValue((100 * counter / len(ql_list)))
            # del layer
            # del dataSource
        QMessageBox.information(None, 'Result',
                                u'Готово!\nСоздано квиклуков: ' + str(len(ql_list)))
        if self.dlg.browse_on_complete.isChecked():
            os.startfile(dst_dir_path)


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
import os
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from helper_main_dialog import HelperDialog
import os.path
# импорт моих функциональных модулей
import ql_exporter
import auxiliary_functions

from temp_my_ellipsoidal_area import ellipsoidal_area


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
        self.last_used_path = None
        self.satellite_handler = auxiliary_functions.Satellite()
        self.layer_handler = auxiliary_functions.Layers()

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
        self.populateComboBox(self.dlg.SENSOR, self.satellite_handler.get_sat_list(), u'Какой спутник ищем?', True)
        self.dlg.INPUT.setText(u'Где взять исходные файлы?')
        self.dlg.OUTPUT.setText(u"Укажите выходную директорию")

        # ellipsoidal_area
        self.ellipsoidal_area_settings()
        self.dlg.options_widget.hide()

    def runGui(self):
        self.dlg.SENSOR.currentIndexChanged.connect(lambda: self.satellite_handler.set_curr_sat(self.dlg.SENSOR.currentText()))
        self.dlg.SENSOR.currentIndexChanged.connect(
            lambda: (QMessageBox.information(
                None, u'Работа с GF/ZY',
                u'Программа НЕ работает с RAR-архивами, поэтому:\n1. Извлеки содержимое RAR-архивов с данными GF/ZY:\n'
                u'(можно извлечь всё в одну папку, можно извлечь каждый архив в отдельный каталог)\n'
                u'2. Запакуй ВСЕ извлечённые данные в ZIP-архив\n'
                u'3. Ура') if self.satellite_handler.get_curr_sat() == "GF1-2, ZY3" else ''))
        self.dlg.INPUTbrowse.clicked.connect(
            lambda: self.set_input_file(sensor=self.satellite_handler.get_curr_sat()))
        self.dlg.OUTPUTbrowse.clicked.connect(
            lambda: self.select_output_dir())
        self.dlg.START.clicked.connect(self.start_processing)

        # ellipsoidal_area
        self.dlg.ellipsoidal_pushButton.clicked.connect(
            lambda:
            ellipsoidal_area(unicode(self.dlg.LAYERcomboBox.currentText()), 'WGS84', 'area_a',
                             u'км²' if self.dlg.radioButton_km_sq.isChecked()
                             else u'Га' if self.dlg.radioButton_Ha.isChecked() else u'м²',
                             self.dlg.area_out_file_lineEdit.text(),
                             self.dlg.ellipsoidal_progressBar, self.dlg.AREAtextBrowser))

        self.dlg.Aux_param_checkBox.stateChanged.connect(self.show_options)
        self.dlg.area_out_pushButton.clicked.connect(self.set_output_file)

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

    #  TODO разобраться с окончаниями elif - в конце можно убрать дубликаты кода
    def set_input_file(self, sensor):

        if sensor == 'BKA':
            file_format = u' БКА (*.kml *.kmz *.KML *.KMZ)'
        elif sensor == 'DEIMOS2':
            file_format = u' Deimos-2 (*.zip *.ZIP *.kmz *.KMZ)'
        elif sensor == 'TH':
            file_format = u' TH (*.zip *.ZIP)'
        elif sensor == 'GF1-2, ZY3':
            file_format = u'GF1-2, ZY3 (*.zip *.ZIP)'
        elif sensor == 'TRIPLESAT':
            file_format = u' TRIPLESAT (*.zip *.ZIP)'
        else:
            file_format = u'??? (Сенсор не задан)'
        src_file_path = QFileDialog.getOpenFileName(
                self.dlg, u"Укажите файл контура ", auxiliary_functions.lastUsedDir(), file_format)
        if not src_file_path:
            return None
        else:
            auxiliary_functions.setLastUsedDir(src_file_path)
            src_file_path = os.path.normpath(src_file_path)
            self.dlg.INPUT.setText(src_file_path)
            out_dir = os.path.join(os.path.dirname(src_file_path), 'QuickLooks')
            self.dlg.OUTPUT.setText(out_dir)

    def set_output_file(self):
        dst_file_path = QFileDialog.getSaveFileName(
            self.dlg, u"Где сохранить файл?", auxiliary_functions.lastUsedDir(), u'SHP-файл (*.shp *.SHP)')
        if not dst_file_path:
            return None
        else:
            auxiliary_functions.setLastUsedDir(os.path.dirname(dst_file_path))
            dst_file_path = os.path.normpath(dst_file_path)
            self.dlg.area_out_file_lineEdit.setText(dst_file_path)

    def select_output_dir(self):
        out_dir = QFileDialog.getExistingDirectory(
            self.dlg, u"Укажите файл контура ", auxiliary_functions.lastUsedDir(type='out'))
        if not out_dir:
            return None
        else:
            self.dlg.OUTPUT.setText(str(os.path.join(out_dir, 'QuickLooks')))
            auxiliary_functions.setLastUsedDir(out_dir, type='out')

    def observe_progress(self, callback=None):
        """Функция для отслеживания прогресса обработки в ql_exporter с помощью callbacks"""
        try:
            for response in callback:
                percent, file_number, process_done_flag = response[0], response[1], response[2]
                self.dlg.progressBar.setValue(percent)
                if process_done_flag is True:
                    QMessageBox.information(None, 'Result',
                                            u'Готово!\nСоздано квиклуков: ' + str(file_number))
                    if process_done_flag is True and file_number == 0:
                        QMessageBox.warning(None, u'Внимание!',
                                                u'Не извлечено ни одного изображения! Проверьте состав входного файла')


        except TypeError:
            print('callback function must be a generator function that yields integer values')
            raise

    def start_processing(self):
        sensor = self.satellite_handler.get_curr_sat()
        source_file = self.dlg.INPUT.text()
        dst_path = auxiliary_functions.make_out_dir(self.dlg.OUTPUT.text())
        if sensor == 'BKA':
            self.observe_progress(ql_exporter.bka_ql_exporter(source_file, dst_path))
        elif sensor == 'DEIMOS2':
            self.observe_progress(ql_exporter.deimos_ql_exporter(source_file, dst_path))
        elif sensor == 'TH' or sensor == 'TRIPLESAT' or sensor == 'GF1-2, ZY3':
            self.observe_progress(ql_exporter.chinease_ql_exporter(source_file, dst_path, sensor))
        # TODO вынести аргумент dst_path в единое место?
        if self.dlg.browse_on_complete.isChecked():
            os.startfile(dst_path)
        self.dlg.progressBar.setValue(0)

    def ellipsoidal_area_settings(self):
        # populate local module GUI
        layers = self.layer_handler.get_layer_name_list()
        self.populateComboBox(self.dlg.LAYERcomboBox, layers, '', True)

    def show_options(self):
        if self.dlg.Aux_param_checkBox.isChecked():
            self.dlg.options_widget.show()
        else:
            self.dlg.options_widget.hide()

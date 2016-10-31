#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import contextlib
import tempfile
from PyQt4.QtCore import *
from qgis.core import *


def make_out_dir(dst_dirpath):
    """Функия берет путь и создаёт в нём каталог QuickLooks, возвращая его путь dst_dir_path"""
    dst_dir_name = 'QuickLooks'
    dst_dir_path = os.path.join(dst_dirpath, dst_dir_name)
    if not os.path.exists(dst_dir_path):
        os.makedirs(dst_dir_path)
    return dst_dir_path


@contextlib.contextmanager
def make_temp_directory():
    """Добавляет возможность создавать временную директорию с помощью контекста with (отсутствует в pyhton 2)"""
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)


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
        self.sat_list = ["DEIMOS2", "BKA", "TH", "GF1-2, ZY3", "TRIPLESAT"]
        # "KAZEOSAT1", "KAZEOSAT2", "ALOS",
        #                  "PRISM",
        #                  "DG/WV-QB-IK-GE", "SPOT5", "SPOT67", "KOMPSAT2", "KOMPSAT3", ]

    def get_sat_list(self):
        return self.sat_list

    def set_curr_sat(self, new_satellite_value):
        self.satellite = new_satellite_value
        return self.satellite

    def get_curr_sat(self):
        return self.satellite


class Layers:
    def __init__(self):
        self.layer_obj_list = None
        self.update_layer_obj_list()

    def update_layer_obj_list(self):
        self.layer_obj_list = QgsMapLayerRegistry.instance().mapLayers()

    def get_layer_name_list(self, lyr_type='vector'):
        # TODO, может, обойтись без словаря?
        types = {'vector': QgsMapLayer.VectorLayer, 'raster': QgsMapLayer.RasterLayer}
        layer_name_list = [layer.name() for layer in QgsMapLayerRegistry.instance().mapLayers().values() if
                           layer.type() == types[lyr_type]]
        return layer_name_list

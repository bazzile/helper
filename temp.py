#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import xml.etree.ElementTree as ET
from string import Template
from PIL import Image
from StringIO import StringIO
import zipfile
import requests
import contextlib
import tempfile
from ql_exporter import tab_template


def deimos_ql_exporter(source_file, dst_dirpath):
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
        ql_list = [f for dp, dn, filenames in os.walk(tmpdir) for f in filenames if f.endswith(('.kmz', '.KMZ')) and f[-7:-4] != 'ALL']
        print(len(ql_list))
        for dirpath, dirnames, filenames in os.walk(tmpdir):
            for filename in filenames:
                g = [filename for filename in filenames]
                print(len(g))
                if filename.endswith(('.kmz', '.KMZ')) and filename[-7:-4] != 'ALL':
                    in_file = os.path.join(dirpath, filename)
                    with zipfile.ZipFile(in_file, 'r') as kmz:
                        with kmz.open('doc.kml', 'r') as kml:
                            kml_tree = ET.parse(kml)
                        # kml_file = kmz.open('doc.kml', 'r')
                    # kmz = zipfile.ZipFile(in_file, 'r')
                    # kml_file = kmz.open('doc.kml', 'r')
                    # kml_tree = ET.parse(kml_file)
                    root = kml_tree.getroot()
                    ql_kml_list = root.findall(".//{http://earth.google.com/kml/2.1}GroundOverlay")
                    counter = 0
                    for q in range(len(ql_kml_list)):
                        ql_filename = ql_kml_list[q].find(".//{http://earth.google.com/kml/2.1}name").text
                        standard_ql_name = ql_filename[11:]
                        ql_dst_path = os.path.join(dst_dir_path, standard_ql_name + '.jpg')
                        ql_url = ql_kml_list[q].find(".//{http://earth.google.com/kml/2.1}href").text
                        response = requests.get(ql_url)
                        if response.status_code == 200:
                            i = Image.open(StringIO(response.content))
                            i.save(ql_dst_path, format='JPEG', quality=100)
                        else:
                            # TODO выводить ошибку "не удалось скачать квиклук с сервера DEIMOS
                            raise IOError
                        ql_image_obj = Image.open(ql_dst_path)
                        ql_width, ql_height = ql_image_obj.size[0], ql_image_obj.size[1]
                        north = ql_kml_list[q].find(".//{http://earth.google.com/kml/2.1}north").text
                        south = ql_kml_list[q].find(".//{http://earth.google.com/kml/2.1}south").text
                        east = ql_kml_list[q].find(".//{http://earth.google.com/kml/2.1}east").text
                        west = ql_kml_list[q].find(".//{http://earth.google.com/kml/2.1}west").text
                        c1, c2, c3, c4 = ','.join((str(west), str(north))), ','.join((str(east), str(north))), \
                                         ','.join((str(east), str(south))), ','.join((str(west), str(south)))
                        print c1, c2, c3, c4
                        text_content = tab_template('deimos', standard_ql_name, c1, c2, c3, c4, ql_height, ql_width)
                        with open(os.path.join(dst_dir_path, standard_ql_name + '.tab'), 'w') as f:
                            f.write(text_content.strip())
                        counter += 1
                break
deimos_ql_exporter(r"C:\Users\lobanov\.qgis2\python\plugins\Helper\testData\DEIMOS\2016-09-27_6izMHfLhb5.zip",
                   r"C:\Users\lobanov\.qgis2\python\plugins\Helper\testData\DEIMOS")

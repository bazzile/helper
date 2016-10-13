#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import xml.etree.ElementTree as ET
from string import Template
from PIL import Image
from StringIO import StringIO
import zipfile
import contextlib
import tempfile
import ogr
from ql_exporter import tab_template


# TODO убрать это
dir = os.path.dirname(__file__)
src_path = os.path.join(dir, r"testData\TH\185205596")
dst_dir_path = os.path.join(dir, src_path)

src_file =r"C:\Users\lobanov\.qgis2\python\plugins\Helper\testData\TH\185205596\185205596.shp"
src_zip_file = r"testData\TH\185205596.zip"


def th_ql_exporter(source_file, dst_dirpath):
    src_file = source_file
    dst_dir_name = 'QuickLooks'
    dst_dir_path = os.path.join(dst_dirpath, dst_dir_name)
    if not os.path.exists(dst_dir_path):
        os.makedirs(dst_dir_path)

    @contextlib.contextmanager
    def make_temp_directory():
        temp_dir = tempfile.mkdtemp()
        try:
            yield temp_dir
        finally:
            shutil.rmtree(temp_dir)

    def get_ql_path(qiucklook_name):
        for ql_path in ql_path_list:
            if qiucklook_name == ql_path.split('.')[-2][-46:-4]:
                return ql_path

    with make_temp_directory() as tmpdir:
        with zipfile.ZipFile(src_zip_file, 'r') as zfile:
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
        for img_contour in layer:
            ql_name = img_contour.GetField('ImgIdDgp')
            geometry = img_contour.GetGeometryRef()
            ring = geometry.GetGeometryRef(0)
            # numpoints = ring.GetPointCount()
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
                'TH', ql_name + '_Bro', coord_list[0], coord_list[3], coord_list[2], coord_list[1], ql_height, ql_width)
            with open(os.path.join(dst_dir_path, ql_name + '_Bro' + '.tab'), 'w') as f:
                f.write(text_content.strip())
        del layer, dataSource
th_ql_exporter(src_zip_file, r"C:\Users\lobanov\.qgis2\python\plugins\Helper\testData\TH")

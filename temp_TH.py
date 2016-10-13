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


def get_ql_path(qiucklook_name):
    for ql_path in ql_path_list:
        if qiucklook_name == ql_path.split('.')[-2][-46:-4]:
            return ql_path

ql_path_list = []
for dirpath, dirnames, filenames in os.walk(os.path.join(dir, src_path)):
    counter = 0
    for filename in filenames:
        if filename.endswith(('.jpg', '.JPG')):
            ql_path_list.append(os.path.join(dirpath, filename))
            # TODO if filename == d[name} for d in [listof_dicts]: ...

ql_list = []
driver = ogr.GetDriverByName('ESRI Shapefile')
dataSource = driver.Open(src_file, 0)
layer = dataSource.GetLayer(0)
for img_contour in layer:
    ql_name = img_contour.GetField('ImgIdDgp')
    geometry = img_contour.GetGeometryRef()
    ring = geometry.GetGeometryRef(0)
    numpoints = ring.GetPointCount()
    coord_list = ['', '', '', '']
    list_counter = 0
    for point_id in range(ring.GetPointCount() - 1):
        lon, lat, z = ring.GetPoint(point_id)
        coord_list[list_counter] = str(','.join((str(lon), str(lat))))
        list_counter += 1
    print('\n')
    ql_path = get_ql_path(ql_name)
    ql_image_obj = Image.open(ql_path)
    ql_width, ql_height = ql_image_obj.size[0], ql_image_obj.size[1]
    text_content = tab_template(
        'TH', ql_name + '_Bro', coord_list[0], coord_list[3], coord_list[2], coord_list[1], ql_height, ql_width)
    with open(os.path.join(dst_dir_path, ql_name + '_Bro' + '.tab'), 'w') as f:
        f.write(text_content.strip())
dataSource = None

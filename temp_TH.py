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


# TODO убрать это
dir = os.path.dirname(__file__)
src_path = os.path.join(dir, r"testData\TH\185205596")

src_file =r"C:\Users\lobanov\.qgis2\python\plugins\Helper\testData\TH\185205596\185205596.shp"

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
    print(ql_name)
    geometry = img_contour.GetGeometryRef()
    ring = geometry.GetGeometryRef(0)
    numpoints = ring.GetPointCount()
    for point_id in range(ring.GetPointCount() - 1):
        lon, lat, z = ring.GetPoint(point_id)
        print (','.join((str(lat), str(lon))))
    print('\n')
dataSource = None

for ql_path in ql_path_list:
    print(ql_path)
    print ql_path.split('.')[-2][-46:-22]
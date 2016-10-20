#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
from osgeo import ogr
from PIL import Image
from ql_exporter import tab_template
from auxiliary_functions import make_out_dir

src_path = r"C:\Users\lobanov\.qgis2\python\plugins\Helper\testData\ZY"
dst_path = make_out_dir(src_path)


def zy_ql_exporter(source_dir, dst_dirpath=None):
    for dirpath, dirnames, filenames in os.walk(source_dir):
        for filename in filenames:
            if filename.endswith(('.shp', '.SHP')):
                shape_filepath = os.path.join(dirpath, filename)
                driver = ogr.GetDriverByName('ESRI Shapefile')
                dataSource = driver.Open(shape_filepath, 0)
                layer = dataSource.GetLayer(0)
                ql_list = layer.GetFeatureCount()
                counter = 0
                for img_contour in layer:
                    ql_name_w_type = img_contour.GetField('browsefile')
                    ql_name = os.path.splitext(img_contour.GetField('browsefile'))[0]
                    geometry = img_contour.GetGeometryRef()
                    ring = geometry.GetGeometryRef(0)
                    coord_list = ['', '', '', '']
                    list_counter = 0
                    for point_id in range(ring.GetPointCount() - 1):
                        lon, lat, z = ring.GetPoint(point_id)
                        coord_list[list_counter] = str(','.join((str(lon), str(lat))))
                        list_counter += 1
                    ql_path = os.path.join(os.path.dirname(shape_filepath), ql_name_w_type)
                    ql_dst_path = os.path.join(dst_dirpath, ql_name_w_type)
                    shutil.copy(ql_path, ql_dst_path)
                    ql_image_obj = Image.open(ql_path)
                    ql_width, ql_height = ql_image_obj.size[0], ql_image_obj.size[1]
                    del ql_image_obj
                    text_content = tab_template(
                        'ZY', ql_name, coord_list[0], coord_list[3], coord_list[2], coord_list[1],
                        ql_height, ql_width)
                    with open(os.path.join(dst_dirpath, ql_name + '.tab'), 'w') as f:
                        f.write(text_content.strip())
                    counter += 1
                    percent_done = 100 * counter / ql_list


zy_ql_exporter(src_path, dst_path)

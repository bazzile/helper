#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import xml.etree.ElementTree as ET
from string import Template
from PIL import Image
import zipfile


def bka_ql_exporter(source_file, dst_dirpath, open_on_finish=True):
    src_file = source_file
    # TODO название директории dst_dir_name/path должно выбираться из Helper
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
    for q in range(len(ql_kml_list)):
        ql_filename = ql_kml_list[q].find(".//href").text
        standard_ql_name = ql_filename[:13]
        # стандартизируем имя и копируем квиклук в целевую директорию, где измеряем его пикс. ширину и высоту
        ql_dst_path = os.path.join(dst_dir_path, standard_ql_name + '.jpg')
        if src_file.endswith(('.kml', '.KML')):
            shutil.copy(os.path.join(dst_dir_path, ql_filename), ql_dst_path)
        else:
            with zipfile.ZipFile(src_file) as kmz:
                with kmz.open(ql_filename) as zipped_ql, open(ql_dst_path, 'wb') as f:
                    shutil.copyfileobj(zipped_ql, f)
        ql_image_obj = Image.open(ql_dst_path)
        ql_width, ql_height = ql_image_obj.size[0], ql_image_obj.size[1]
        coords_str = ql_kml_list[q].find(".//coordinates").text
        # преобразуем строку с координатами углов в список и разбиваем по 4 точкам
        coords_lst = coords_str.split('\n')
        c1, c2, c3, c4 = coords_lst[3], coords_lst[0], coords_lst[1], coords_lst[2]
        text_content = Template('!table\n'
                                '!version 300\n'
                                '!charset WindowsCyrillic\n'
                                'Definition Table\n'
                                '  File "$file_name"\n'
                                '  Type "RASTER"\n'
                                '  ($map_coords1)  (0.0,0.0) Label "Point 1",\n'
                                '  ($map_coords2)  (0.0,$img_hight.0) Label "Point 2",\n'
                                '  ($map_coords3)  ($img_width.0,$img_hight.0) Label "Point 3",\n'
                                '  ($map_coords4)  ($img_width.0,0.0) Label "Point 4"\n'
                                ' CoordSys Earth Projection 1, 0\n')
        text_content = text_content.substitute(
            file_name=standard_ql_name + '.jpg', map_coords1=c1, map_coords2=c2, map_coords3=c3, map_coords4=c4,
            img_hight=str(ql_height), img_width=str(ql_width))

        with open(os.path.join(dst_dir_path, standard_ql_name + '.tab'), 'w') as f:
            f.write(text_content.strip())
        # self.dlg.progressBar.setValue(50)
    if open_on_finish is True:
        os.startfile(dst_dir_path)
    else:
        pass

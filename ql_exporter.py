#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import xml.etree.ElementTree as ET
from string import Template
from PIL import Image
from StringIO import StringIO
import zipfile
import urllib
from osgeo import ogr
import auxiliary_functions


def tab_template(sensor, file_name, map_coords1, map_coords2, map_coords3, map_coords4, img_hight, img_width):
    """Функция, формирующая tab-файл привязки по шаблону, используя следующие параметры
    :param file_type:
    :param file_name:
    :param map_coords1:
    :param map_coords2:
    :param map_coords3:
    :param map_coords4:
    :param img_hight:
    :type img_width: int
    """
    # порядок следования точек у некоторых спутников отличается, поэтому строки будут разные
    if sensor == 'bka':
        point2 = '  ($map_coords2)  (0.0,$img_hight.0) Label "Point 2",\n'
        point4 = '  ($map_coords4)  ($img_width.0,0.0) Label "Point 4"\n'
    elif sensor == 'deimos':
        point2 = '  ($map_coords2)  ($img_width.0,0.0) Label "Point 2",\n'
        point4 = '  ($map_coords4)  (0.0,$img_hight.0) Label "Point 4"\n'
    else:
        point2 = '  ($map_coords2)  (0.0,$img_hight.0) Label "Point 2",\n'
        point4 = '  ($map_coords4)  ($img_width.0,0.0) Label "Point 4"\n'
    text_content = Template('!table\n'
                            '!version 300\n'
                            '!charset WindowsCyrillic\n\n'
                            'Definition Table\n'
                            '  File "$file_name"\n'
                            '  Type "RASTER"\n'
                            '  ($map_coords1)  (0.0,0.0) Label "Point 1",\n' + point2 +
                            # '  ($map_coords2)  (0.0,$img_hight.0) Label "Point 2",\n'
                            '  ($map_coords3)  ($img_width.0,$img_hight.0) Label "Point 3",\n' + point4 +
                            # '  ($map_coords4)  ($img_width.0,0.0) Label "Point 4"\n'
                            ' CoordSys Earth Projection 1, 0\n')
    return text_content.substitute(
        file_name=os.path.splitext(file_name)[0] + '.jpg', map_coords1=map_coords1, map_coords2=map_coords2,
        map_coords3=map_coords3, map_coords4=map_coords4, img_hight=str(img_hight), img_width=str(img_width))


def get_valid_column_name(col_name_list, layer):
    img_name = None
    for col_name in col_name_list:
        img_contour = layer.GetFeature(0)
        try:
            img_name = img_contour.GetField(col_name)
            if img_name is not None:
                return col_name
        except ValueError:
            continue
    if img_name is None:
        # TODO почему ошибка не вылазит?
        raise ValueError(u'Поля {} не содержат названия снимков. Проверье shp-файл'.format(str(col_name_list)))


def bka_ql_exporter(source_file, dst_dirpath):
    total_ql_list, percent_done, process_done_flag = 0, 0, False
    # парсим kml
    if source_file.endswith(('.kml', '.KML')):
        tree = ET.parse(source_file)
    else:
        # src_file.endswith(('.kmz', '.KMZ'))
        with zipfile.ZipFile(source_file) as kmz:
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
    counter = 0
    for q in range(len(ql_kml_list)):
        ql_filename = ql_kml_list[q].find(".//href").text
        standard_ql_name = ql_filename[:13]
        # стандартизируем имя и копируем квиклук в целевую директорию, где измеряем его пикс. ширину и высоту
        ql_dst_path = os.path.join(dst_dirpath, standard_ql_name + '.jpg')
        if source_file.endswith(('.kml', '.KML')):
            shutil.copy(os.path.join(os.path.dirname(source_file), ql_filename), ql_dst_path)
        else:
            with zipfile.ZipFile(source_file) as kmz:
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
        with open(os.path.join(dst_dirpath, standard_ql_name + '.tab'), 'w') as f:
            f.write(text_content.strip())
        counter += 1
        percent_done = 100 * counter / len(ql_kml_list)
        # этот callback позволяет отслеживать прогресс функции в helper_main
        yield percent_done, len(ql_kml_list), process_done_flag
    process_done_flag = True
    yield percent_done, len(ql_kml_list), process_done_flag


def deimos_ql_exporter(source_file, dst_dirpath):
    total_ql_list, percent_done, process_done_flag = 0, 0, False
    with auxiliary_functions.make_temp_directory() as tmpdir:
        with zipfile.ZipFile(source_file, 'r') as zfile:
            zfile.extractall(tmpdir)
            ql_list = [f for dp, dn, filenames in os.walk(tmpdir) for f in filenames if f.endswith(('.kmz', '.KMZ'))
                       and f[-7:-4] != 'ALL']
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
                        ql_dst_path = os.path.join(dst_dirpath, standard_ql_name + '.jpg')
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
                        with open(os.path.join(dst_dirpath, standard_ql_name + '.tab'), 'w') as f:
                            f.write(text_content.strip())
                        counter += 1
                        percent_done = 100 * counter / len(ql_list)
                        # этот callback позволяет отслеживать прогресс функции в helper_main
                        yield percent_done, len(ql_list), process_done_flag
                    total_ql_list += len(ql_list)
    process_done_flag = True
    yield percent_done, total_ql_list, process_done_flag


def chinease_ql_exporter(source_file, dst_dirpath, sensor):
    total_ql_list, percent_done, process_done_flag = 0, 0, False
    if source_file.endswith(('.zip', '.ZIP')):
        with auxiliary_functions.make_temp_directory() as tmpdir:
            with zipfile.ZipFile(source_file, 'r') as zfile:
                zfile.extractall(tmpdir)
    # else:
    #     if os.path.isdir (source_file) do it(make all further proc a function) for each zipfile in directory
            for dirpath, dirnames, filenames in os.walk(tmpdir):
                for filename in filenames:
                    if filename.endswith(('.shp', '.SHP')):
                        shape_filepath = os.path.join(dirpath, filename)
                        driver = ogr.GetDriverByName('ESRI Shapefile')
                        dataSource = driver.Open(shape_filepath, 0)
                        layer = dataSource.GetLayer(0)
                        ql_list = layer.GetFeatureCount()
                        total_ql_list += ql_list
                        if sensor == 'TH':
                            col_name = get_valid_column_name(('ImgIdDgp', 'ImgIdGfb'), layer)
                        else:
                            # вариант GF/ZY/TRIPLESAT
                            col_name = get_valid_column_name(['browsefile', 'browserimg'], layer)
                        counter = 0
                        for img_contour in layer:
                            # ql_name_w_type = img_contour.GetField(col_name)
                            if sensor == 'TH':
                                ql_name_w_type = str(img_contour.GetField(col_name)) + '_Bro' + '.jpg'
                            elif sensor == 'TRIPLESAT' or sensor == 'GF1-2, ZY3':
                                ql_name_w_type = os.path.basename(img_contour.GetField(col_name))
                            # TODO сделать также (функция от ql_name_w_type) в zy
                            ql_name = os.path.splitext(ql_name_w_type)[0]
                            geometry = img_contour.GetGeometryRef()
                            ring = geometry.GetGeometryRef(0)
                            coord_list = ['', '', '', '']
                            list_counter = 0
                            for point_id in range(ring.GetPointCount() - 1):
                                lon, lat, z = ring.GetPoint(point_id)
                                coord_list[list_counter] = str(','.join((str(lon), str(lat))))
                                list_counter += 1
                            if sensor == 'TRIPLESAT':
                                ql_path = os.path.join(os.path.dirname(shape_filepath), 'images', ql_name_w_type)
                            else:
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
                            yield percent_done, ql_list, process_done_flag
                        del layer, dataSource
    process_done_flag = True
    yield percent_done, total_ql_list, process_done_flag


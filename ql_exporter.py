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
    # img_name = None
    for col_name in col_name_list:
        img_contour = layer.GetFeature(0)
        try:
            img_name = img_contour.GetField(col_name)
            if img_name is not None:
                return col_name
        except ValueError:
            continue
    # если дошли до сюда, то тот SHP-файл не содержит нужных полей
    return None


def bka_ql_exporter(source_file, dst_dirpath):
    total_ql_list, percent_done, process_done_flag = 0, 0, False
    # парсим kml
    if source_file.endswith(('.kml', '.KML')):
        with open(source_file, 'r') as kml_file:
            kml_xml = kml_file.read()
    else:
        # src_file.endswith(('.kmz', '.KMZ'))
        with zipfile.ZipFile(source_file) as kmz:
            for filename in kmz.namelist():
                if filename.endswith(('.kml', '.KML')):
                    # парсим kml
                    with kmz.open(filename, 'r') as kml_file:
                        kml_xml = kml_file.read()
                    break
    tree = auxiliary_functions.remove_xml_namespace(kml_xml)
    root = tree.root
    # ищем в kml все записи, описывающие квиклук
    ql_kml_list = root.findall(".//GroundOverlay")
    counter = 0
    for q in range(len(ql_kml_list)):
        ql_rel_path = ql_kml_list[q].find(".//href").text
        ql_name = os.path.splitext(os.path.basename(ql_rel_path))[0]
        # стандартизируем имя и копируем квиклук в целевую директорию, где измеряем его пикс. ширину и высоту
        ql_dst_path = os.path.join(dst_dirpath, ql_name + '.jpg')
        if source_file.endswith(('.kml', '.KML')):
            shutil.copy(os.path.join(os.path.dirname(source_file), ql_rel_path), ql_dst_path)
        else:
            with zipfile.ZipFile(source_file) as kmz:
                # заменяем слеши, чтобы работать с zip-архивом
                with kmz.open(ql_rel_path.replace('\\', '/')) as zipped_ql, open(ql_dst_path, 'wb') as f:
                    shutil.copyfileobj(zipped_ql, f)
        ql_image_obj = Image.open(ql_dst_path)
        ql_width, ql_height = ql_image_obj.size[0], ql_image_obj.size[1]
        del ql_image_obj
        coords_str = ql_kml_list[q].find(".//coordinates").text
        # предусматриваем необычный вариант хранения координат (X,Y,Z в одну строчку)
        coords_str = coords_str.strip().replace(',0 ', '\n')
        # преобразуем строку с координатами углов в список и разбиваем по 4 точкам
        coords_lst = coords_str.split('\n')
        c1, c2, c3, c4 = coords_lst[3], coords_lst[0], coords_lst[1], coords_lst[2]
        text_content = tab_template('bka', ql_name, c1, c2, c3, c4, ql_height, ql_width)
        with open(os.path.join(dst_dirpath, ql_name + '.tab'), 'w') as f:
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
            if source_file.lower().endswith('.zip'):
                ql_list = [f for dp, dn, filenames in os.walk(tmpdir) for f in filenames if f.endswith(('.kmz', '.KMZ'))
                           and f[-7:-4] != 'ALL']
            else:
                ql_list = [os.path.join(dp, filename) for dp, dn, filenames in os.walk(tmpdir)
                           for filename in filenames if filename.lower().endswith('.png')]
        if source_file.lower().endswith('.kmz'):
            for dirpath, dirnames, filenames in os.walk(tmpdir):
                counter = 0
                for filename in [filename for filename in filenames if filename.lower().endswith('.kml')]:
                    with open(os.path.join(dirpath, filename)) as kml_file:
                        kml_xml = kml_file.read()
                        tree = auxiliary_functions.remove_xml_namespace(kml_xml)
                        root = tree.root
                        # TODO отсюда и далее до break код полностью дублируется в else. Устранить (функция?)
                        ql_kml_list = root.findall(".//GroundOverlay")
                        for q in range(len(ql_kml_list)):
                            ql_filename = ql_kml_list[q].find(".//name").text
                            ql_dst_path = os.path.join(dst_dirpath, ql_filename + '.tif')
                            ql_url = ql_kml_list[q].find(".//href").text
                            i = Image.open(os.path.join(tmpdir, ql_url))
                            i.save(ql_dst_path, format='TIFF')
                            del i
                            ql_image_obj = Image.open(ql_dst_path)
                            ql_width, ql_height = ql_image_obj.size[0], ql_image_obj.size[1]
                            del ql_image_obj
                            north = ql_kml_list[q].find(".//north").text
                            south = ql_kml_list[q].find(".//south").text
                            east = ql_kml_list[q].find(".//east").text
                            west = ql_kml_list[q].find(".//west").text
                            c1, c2, c3, c4 = ','.join((str(west), str(north))), ','.join((str(east), str(north))), \
                                             ','.join((str(east), str(south))), ','.join((str(west), str(south)))
                            text_content = tab_template('deimos', ql_filename, c1, c2, c3, c4, ql_height, ql_width)
                            with open(os.path.join(dst_dirpath, ql_filename + '.tab'), 'w') as f:
                                f.write(text_content.strip())
                            counter += 1
                            percent_done = 100 * counter / len(ql_list)
                            # этот callback позволяет отслеживать прогресс функции в helper_main
                            yield percent_done, len(ql_list), process_done_flag
                        total_ql_list += len(ql_kml_list)
                    break
        else:
            for dirpath, dirnames, filenames in os.walk(tmpdir):
                counter = 0
                for filename in filenames:
                    if filename.endswith(('.kmz', '.KMZ')) and filename[-7:-4] != 'ALL':
                        in_file = os.path.join(dirpath, filename)
                        with zipfile.ZipFile(in_file, 'r') as kmz:
                            with kmz.open('doc.kml', 'r') as kml_file:
                                kml_xml = kml_file.read()
                                tree = auxiliary_functions.remove_xml_namespace(kml_xml)
                                root = tree.root
                        ql_kml_list = root.findall(".//GroundOverlay")
                        for q in range(len(ql_kml_list)):
                            ql_filename = ql_kml_list[q].find(".//name").text
                            ql_dst_path = os.path.join(dst_dirpath, ql_filename + '.tif')
                            ql_url = ql_kml_list[q].find(".//href").text
                            content = StringIO(urllib.urlopen(ql_url).read())
                            i = Image.open(content)
                            i.save(ql_dst_path, format='TIFF')
                            del i
                            ql_image_obj = Image.open(ql_dst_path)
                            ql_width, ql_height = ql_image_obj.size[0], ql_image_obj.size[1]
                            del ql_image_obj
                            north = ql_kml_list[q].find(".//north").text
                            south = ql_kml_list[q].find(".//south").text
                            east = ql_kml_list[q].find(".//east").text
                            west = ql_kml_list[q].find(".//west").text
                            c1, c2, c3, c4 = ','.join((str(west), str(north))), ','.join((str(east), str(north))), \
                                             ','.join((str(east), str(south))), ','.join((str(west), str(south)))
                            text_content = tab_template('deimos', ql_filename, c1, c2, c3, c4, ql_height, ql_width)
                            with open(os.path.join(dst_dirpath, ql_filename + '.tab'), 'w') as f:
                                f.write(text_content.strip())
                            counter += 1
                            percent_done = 100 * counter / len(ql_list)
                            # этот callback позволяет отслеживать прогресс функции в helper_main
                            yield percent_done, len(ql_list), process_done_flag
                        total_ql_list += len(ql_kml_list)
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
                        # если в shp-файле не нашлось нужных полей, откидываем его
                        if col_name is None:
                            total_ql_list -= ql_list
                            yield 100, 0, process_done_flag
                            del layer, dataSource
                            continue
                        for img_contour in layer:
                            # ql_name_w_type = img_contour.GetField(col_name)
                            if sensor == 'TH':
                                ql_name_w_type = str(img_contour.GetField(col_name)) + '_Bro' + '.jpg'
                            elif sensor == 'TRIPLESAT' or sensor == 'GF1-2, ZY3':
                                ql_name_w_type = os.path.basename(img_contour.GetField(col_name))
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
                                'China', ql_name, coord_list[0], coord_list[3], coord_list[2], coord_list[1],
                                ql_height, ql_width)
                            with open(os.path.join(dst_dirpath, ql_name + '.tab'), 'w') as f:
                                f.write(text_content.strip())
                            counter += 1
                            percent_done = 100 * counter / ql_list
                            yield percent_done, ql_list, process_done_flag
                        del layer, dataSource
    process_done_flag = True
    yield percent_done, total_ql_list, process_done_flag

# chinease_ql_exporter(r"C:\Users\lobanov\.qgis2\python\plugins\Helper\testData\TRIPLESAT\2016-10-26_1808644472_exportshp.zip",
#                      r"C:\Users\lobanov\.qgis2\python\plugins\Helper\testData\TRIPLESAT\QuickLooks", r"TRIPLESAT")
deimos_ql_exporter(r"U:\PRJ\2016\HELPER\Geolocation\EXAMPLE\DEIMOS2\version1\2016-09-27_6izMHfLhb5.zip",
                   r"U:\PRJ\2016\HELPER\Geolocation\EXAMPLE\DEIMOS2\version1\QuickLooks")
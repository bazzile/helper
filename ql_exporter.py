#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import xml.etree.ElementTree as ET
from string import Template
from PIL import Image
from StringIO import StringIO
import zipfile
# import requests
from osgeo import ogr
import contextlib
import tempfile


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
        file_name=file_name.split('.')[0] + '.jpg', map_coords1=map_coords1, map_coords2=map_coords2,
        map_coords3=map_coords3, map_coords4=map_coords4, img_hight=str(img_hight), img_width=str(img_width))


def deimos_ql_exporter(source_file, dst_dirpath, open_on_finish=True):
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
        ql_list = len([name for name in os.listdir(r"C:\NextGIS_QGIS\apps\qgis\python\plugins\Helper\testData\BKA\QuickLooks") if
             name.endswith(('.kmz', '.KMZ')) and name[-7:-4] != 'ALL'])
        for dirpath, dirnames, filenames in os.walk(tmpdir):
            for filename in filenames:
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
                        ql_dst_path = os.path.join(dst_dirpath, standard_ql_name + '.jpg')
                        ql_url = ql_kml_list[q].find(".//{http://earth.google.com/kml/2.1}href").text
                        response = requests.get(ql_url)
                        if response.status_code == 200:
                            i = Image.open(StringIO(response.content))
                            i.save(ql_dst_path, format='JPEG', subsampling=0, quality=100)
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
                break


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
            shutil.copy(os.path.join(os.path.dirname(src_file), ql_filename), ql_dst_path)
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
    # dlg.progressBar.setValue(50)
    if open_on_finish is True:
        os.startfile(dst_dir_path)
    else:
        pass


def th_ql_exporter(source_file, dst_dirpath):
    src_file = source_file

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
        with zipfile.ZipFile(src_file, 'r') as zfile:
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
        ql_list = layer.GetFeatureCount()
        counter = 0
        print counter
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
            ql_dst_path = os.path.join(dst_dirpath, ql_name + '_Bro' + '.jpg')
            shutil.copy(ql_path, ql_dst_path)
            ql_image_obj = Image.open(ql_path)
            ql_width, ql_height = ql_image_obj.size[0], ql_image_obj.size[1]
            del ql_image_obj
            text_content = tab_template(
                'TH', ql_name + '_Bro', coord_list[0], coord_list[3], coord_list[2], coord_list[1], ql_height, ql_width)
            with open(os.path.join(dst_dirpath, ql_name + '_Bro' + '.tab'), 'w') as f:
                f.write(text_content.strip())
            counter += 1
            percent_done = 100 * counter / ql_list
            yield percent_done, ql_list
        del layer, dataSource

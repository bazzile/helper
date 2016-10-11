# -*- coding: utf-8 -*-
import os
import shutil
import xml.etree.ElementTree as ET
import zipfile
from PIL import Image
from StringIO import StringIO
from ql_exporter import tab_template
# from hurry.filesize import size
import requests
from tempfile import TemporaryFile


# TODO убрать это
dir = os.path.dirname(__file__)
in_file = r"E:\RASTER\test\doc.kml"
dst_dir_path = os.path.join(dir, r"testData\DEIMOS\2016-09-27_6izMHfLhb5\6izMHfLhb5\2015-08-11_DE2_L0R_000000_20150811T073720_20150811T073723_DE2_6195_73D7")

in_path = os.path.join(os.path.dirname(__file__), r"testData\DEIMOS\2016-09-27_6izMHfLhb5")
# TODO сюда долбануть временную директуорию или zipped zip handler
for dirpath, dirnames, filenames in os.walk(in_path):
    for filename in filenames:
        if filename.endswith(('.kmz', '.KMZ')) and filename[-7:-4] != 'ALL':
            # print(filename)
            in_file = os.path.join(dirpath, filename)
            kmz = zipfile.ZipFile(in_file, 'r')
            kml_file = kmz.open('doc.kml', 'r')
            kml_tree = ET.parse(kml_file)
            root = kml_tree.getroot()

            # TODO реализовать через find .//
            # ищем в kml запись, описывающую квиклук
            # http://stackoverflow.com/questions/14853243/parsing-xml-with-namespace-in-python-via-elementtree
            # if element.tag.endswith('href') или на вход (namespace + tag)
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
                    i.save(ql_dst_path, format='JPEG', subsampling=0, quality=100)
                # r = requests.get(ql_url, stream=True)
                # if r.status_code == 200:
                #     with TemporaryFile() as tempf:
                #
                #             downloaded = 0
                #             # скачиваем файл по кускам в 1024 байта (chunks)
                #             for chunk in r.iter_content(1024):
                #                 downloaded += len(chunk)
                #                 tempf.write(chunk)
                #             # на лету конвертируем изначально полученный png в jpg
                #             i = Image.open(tempf)
                #             i.save(ql_dst_path)
                    # with open(ql_dst_path, 'wb') as f:
                    #         downloaded = 0
                    #         # скачиваем файл по кускам в 1024 байта (chunks)
                    #         for chunk in r.iter_content(1024):
                    #             downloaded += len(chunk)
                    #             f.write(chunk)
                    #             i.save(ql_dst_path)
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

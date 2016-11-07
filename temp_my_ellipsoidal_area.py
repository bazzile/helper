#!/usr/bin/env python
# -*- coding: utf-8 -*-
##Ellipsoidal Area=name
##Utils=group
##input=vector polygon
##ellipsoid=string WGS84
##new_field=string Area
##units=selection sq_km;sq_m;sq_miles;sq_ft;sq_nm;sq_degrees
##output=output vector

import processing
from processing.core.GeoAlgorithmExecutionException import GeoAlgorithmExecutionException
from processing.tools.vector import VectorWriter
from PyQt4.QtCore import *
from qgis.core import *


def ellipsoidal_area(input_lyr_name, ellipsoid, new_field, units, output, progress, text_output):
    input_layer = QgsMapLayerRegistry.instance().mapLayersByName(input_lyr_name)[0]
    if not input_layer.crs().geographicFlag():
        raise GeoAlgorithmExecutionException(
            'Your layer has a Projected CRS. '
            'This script works only on layers with Geographic CRS.')

    fields = QgsFields()
    for field in input_layer.pendingFields():
        if field.name().lower() == new_field.lower():
            raise GeoAlgorithmExecutionException(
                'The input layer already has a field named %s.'
                'Please choose a different name for the Area field.' % new_field)

        fields.append(field)
    fields.append(QgsField(new_field, QVariant.Double))

    if not output:
        # TODO случай просто расчёта без слоя
        pass
    else:
        writer = VectorWriter(output, None, fields,
                              QGis.WKBMultiPolygon, input_layer.crs())
    # Initialize QgsDistanceArea object
    area = QgsDistanceArea()
    area.setEllipsoid(ellipsoid)
    area.setEllipsoidalMode(True)
    area.computeAreaInit()

    out_f = QgsFeature()

    # Get feature count for progress bar
    features = processing.features(input_layer)
    num_features = len(features)

    total_area = 0
    for i, feat in enumerate(features):
        progress.setValue(int(100 * i / num_features))
        geom = feat.geometry()
        polygon_area = 0
        error_features_counter = 0
        try:
            if geom.isMultipart():
                polygons = geom.asMultiPolygon()
                for polygon in polygons:
                    polygon_area += area.measurePolygon(polygon[0])
            else:
                polygon = geom.asPolygon()
                polygon_area = area.measurePolygon(polygon[0])

            # calculated area is in sq. metres (see the "else" case)
            # TODO добавить гектары вместо метров
            if units == u'км²':
                final_area = polygon_area / 1e6
            elif units == u'Га':
                final_area = polygon_area / 10000
            else:
                final_area = polygon_area
            total_area += final_area

            attrs = feat.attributes()
            attrs.append(final_area)
            out_f.setGeometry(geom)
            out_f.setAttributes(attrs)
            # writer.addFeature(out_f)
        except AttributeError:  # если попался тип геометрии NoneType (битая и т.п.)
            error_features_counter += 1
            pass

    progress.setValue(100)
    text_output.setText(u'Имя файла: {}\nКоличество объектов: {}\nОбщая площадь: {} {}{}'
                        .format(input_lyr_name, num_features, total_area, units,
                                u'\nВнимание! В файле встречаются некорректные / битые объекты в количестве {} шт.\n'
                                u'Рекомендуется проверить топологию'.format(error_features_counter)
                                if error_features_counter > 0 else ''))
    # del writer

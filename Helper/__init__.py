# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Helper
                                 A QGIS plugin
 Plungin that helps you with your geospatial routine
                             -------------------
        begin                : 2016-09-28
        copyright            : (C) 2016 by Innoter
        email                : lobanov@innoter.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load Helper class from file Helper.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .helper_main import Helper
    return Helper(iface)

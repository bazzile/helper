#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil


def make_out_dir(dst_dirpath):
    """Функия берет путь и создаёт в нём каталог QuickLooks, возвращая его путь dst_dir_path"""
    dst_dir_name = 'QuickLooks'
    dst_dir_path = os.path.join(dst_dirpath, dst_dir_name)
    if not os.path.exists(dst_dir_path):
        os.makedirs(dst_dir_path)
    return dst_dir_path

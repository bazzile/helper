#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import contextlib
import tempfile


def make_out_dir(dst_dirpath):
    """Функия берет путь и создаёт в нём каталог QuickLooks, возвращая его путь dst_dir_path"""
    dst_dir_name = 'QuickLooks'
    dst_dir_path = os.path.join(dst_dirpath, dst_dir_name)
    if not os.path.exists(dst_dir_path):
        os.makedirs(dst_dir_path)
    return dst_dir_path


@contextlib.contextmanager
def make_temp_directory():
    """Добавляет возможность создавать временную директорию с помощью контекста with (отсутствует в pyhton 2)"""
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)

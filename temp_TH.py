#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import xml.etree.ElementTree as ET
from string import Template
from PIL import Image
from StringIO import StringIO
import zipfile
import contextlib
import tempfile

# TODO убрать это
dir = os.path.dirname(__file__)
src_path = os.path.join(dir, r"testData\TH\185205596")

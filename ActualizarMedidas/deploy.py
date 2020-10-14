#!/usr/bin/env python3

import json
import os
import sys
import winsound

from urllib.parse import urlencode
from urllib.request import Request, urlopen
from pathlib import Path

import zipfile
try:
    import zlib
    import shutil
    compression = zipfile.ZIP_DEFLATED
except ImportError:
    compression = zipfile.ZIP_STORED

version = "0_1"

if __name__=="__main__":
    plugin_folder = Path.home() / r"AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\ActualizarMedidas"
    file_path = Path(__file__)
    parent_dir = file_path.resolve().parent
    grandparent_dir = parent_dir.parent

    meta = parent_dir / "metadata.txt"
    contents = meta.read_text()
    with open(meta, 'w') as fh:
        for line in contents.split('\n'):
            if line.startswith('version'):
                line = 'version=' + version.replace("_", ".")
            if line:
                fh.write(line + '\n')
            else:
                fh.write(line)

    zf = zipfile.ZipFile(grandparent_dir / ('ActualizarMedidas' + version + '.zip'), mode='w')

    try:
        for f in ["ActualizarMedidas.py",
                  "__init__.py",
                  "metadata.txt",
                  "deploy.py",
                  "img/OpenStreetMap_Wikidata_logo.svg",
                  ]:
            zf.write(parent_dir / f, compress_type=compression, arcname=str(Path("OSM_Wikidata") / f))
    except Exception as e:
        for j in range(1,3):
            for i in range(1, 10): winsound.Beep(i * 100, 200)
        raise e
    finally:
        img_dir_in_plugin_folder = plugin_folder / 'img'
        img_dir_in_plugin_folder.mkdir(parents=True, exist_ok=True)
        for p in parent_dir.glob("*"):
            try:
                shutil.copy(p, plugin_folder)
            except (PermissionError, FileNotFoundError):
                pass
        img_dir = parent_dir / 'img'
        img_dir_in_plugin_folder = plugin_folder / 'img'
        img_dir_in_plugin_folder.mkdir(parents=True, exist_ok=True)
        for p in img_dir.glob("*"):
            try:
                shutil.copy(p, img_dir_in_plugin_folder)
            except (PermissionError, FileNotFoundError):
                pass
        print('closing')
        zf.close()


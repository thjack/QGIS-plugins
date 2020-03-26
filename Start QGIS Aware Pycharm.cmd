# @echo off

call "C:\Program Files\QGIS 3.8\bin\o4w_env.bat"

call "C:\Program Files\QGIS 3.8\apps\grass\grass-7.4.0\etc\env.bat"

# @echo off

path %PATH%;"C:\Program Files\QGIS 3.8\apps\qgis\bin"

path %PATH%;"C:\Program Files\QGIS 3.8\apps\grass\grass-7.4.0\lib"

path %PATH%;"C:\Program Files\QGIS 3.8\apps\Qt5\bin"

path %PATH%;"C:\Program Files\QGIS 3.8\apps\Python37\Scripts"

set PYTHONPATH="%PYTHONPATH%;C:\Program Files\QGIS 3.8\apps\qgis\python"

set PYTHONHOME="C:\Program Files\QGIS 3.8\apps\Python37"

start "PyCharm aware of Quantum GIS" /B "C:\Program Files\JetBrains\PyCharm Community Edition 2018.3.4\bin\pycharm64.exe"
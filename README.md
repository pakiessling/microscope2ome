# Wrappers to create .ome.tif from our microscope

1. Create enviroment from .yml
2. python qupath_img2ome.py input_folder output_folder --tile-size 1024 --series 0 -c ZLIB

ome2tif wraps bioformats2raw and raw2ometiff but the output could not be loaded by tifffile and Xenium Explorer
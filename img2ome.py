#!/usr/bin/env python3

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path

def find_images(path):
    """Find all image files in the given path."""
    image_extensions = ['.tif', '.tiff', '.jpg', '.jpeg', '.png', '.nd2', '.czi', '.lif', '.mrxs', '.svs']
    results = []
    if os.path.isfile(path):
        ext = os.path.splitext(path)[1].lower()
        if ext in image_extensions:
            results.append(path)
    else:
        for root, _, files in os.walk(path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in image_extensions:
                    results.append(os.path.join(root, file))
    return results

def convert_image(image_path, output_dir, bf2raw_args, raw2ometiff_args, keep_zarr=False, overwrite=False):
    """Convert a single image to OME-TIFF format."""
    image_name = os.path.splitext(os.path.basename(image_path))[0]
    zarr_dir = os.path.join(output_dir, f"{image_name}.zarr")
    ometiff_path = os.path.join(output_dir, f"{image_name}.ome.tiff")

    # Check if OME-TIFF exists and handle overwrite
    if os.path.exists(ometiff_path):
        if overwrite:
            try:
                os.remove(ometiff_path)
            except OSError as e:
                print(f"Error deleting existing OME-TIFF {ometiff_path}: {e}")
                return False
        else:
            print(f"Skipping {image_path} as output {ometiff_path} exists. Use --overwrite to replace.")
            return True

    # Run bioformats2raw
    bf2raw_cmd = ['bioformats2raw'] + bf2raw_args + [image_path, zarr_dir]
    print(f"Converting {image_path} to zarr format...")
    print(f"Running: {' '.join(bf2raw_cmd)}")
    try:
        subprocess.run(bf2raw_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error converting {image_path} to zarr: {e}")
        return False

    # Run raw2ometiff
    raw2ometiff_cmd = ['raw2ometiff'] + raw2ometiff_args + [zarr_dir, ometiff_path]
    print(f"Converting zarr to OME-TIFF format...")
    print(f"Running: {' '.join(raw2ometiff_cmd)}")
    try:
        subprocess.run(raw2ometiff_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error converting zarr to OME-TIFF: {e}")
        return False

    # Cleanup zarr directory if not keeping it
    if not keep_zarr and os.path.exists(zarr_dir):
        shutil.rmtree(zarr_dir)
    print(f"Successfully converted {image_path} to {ometiff_path}")
    return True

def parse_args():
    parser = argparse.ArgumentParser(description='Convert microscope images to OME-TIFF format.')
    parser.add_argument('input_path', help='Path to image file or directory containing images')
    parser.add_argument('output_dir', help='Directory to save output OME-TIFF files')
    parser.add_argument('--keep-zarr', action='store_true', help='Keep intermediate zarr files')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing output files')
    parser.add_argument('--progress', '-p', action='store_true', help='Show progress bars during conversion')
    
    # bioformats2raw options
    bf2raw_group = parser.add_argument_group('bioformats2raw options')
    bf2raw_group.add_argument('--tile-width', type=int, help='Maximum tile width (default: 1024)')
    bf2raw_group.add_argument('--tile-height', type=int, help='Maximum tile height (default: 1024)')
    bf2raw_group.add_argument('--resolutions', type=int, help='Number of pyramid resolutions to generate')
    bf2raw_group.add_argument('--compression', choices=['null', 'zlib', 'blosc'], help='Compression type for Zarr')
    bf2raw_group.add_argument('--max-workers', type=int, help='Maximum number of workers (default: 4)')
    bf2raw_group.add_argument('--series', help='Comma-separated list of series indexes to convert')
    bf2raw_group.add_argument('--no-minmax', action='store_true', help='Turn off min/max calculation')
    bf2raw_group.add_argument('--memo-directory', help='Directory for .bfmemo cache files')
    bf2raw_group.add_argument('--downsample-type', choices=['SIMPLE', 'GAUSSIAN', 'AREA', 'LINEAR', 'CUBIC', 'LANCZOS'], help='Tile downsampling algorithm')
    
    # raw2ometiff options
    raw2ometiff_group = parser.add_argument_group('raw2ometiff options')
    raw2ometiff_group.add_argument('--ometiff-compression', choices=['UNCOMPRESSED', 'LZW', 'JPEG', 'JPEG_2000', 'JPEG_2000_LOSSY'], default='LZW', help='Compression type for OME-TIFF')
    raw2ometiff_group.add_argument('--ometiff-quality', type=int, help='Compression quality')
    raw2ometiff_group.add_argument('--rgb', action='store_true', help='Write channels as RGB')
    raw2ometiff_group.add_argument('--split', action='store_true', help='Split into multiple OME-TIFF files')
    raw2ometiff_group.add_argument('--split-planes', action='store_true', help='Split into one file per plane')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    return parser.parse_args()

def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    input_path = args.input_path
    input_dir = os.path.dirname(input_path) if os.path.isfile(input_path) else input_path
    image_paths = find_images(input_path)
    
    if not image_paths:
        print(f"No supported images found in {input_path}")
        sys.exit(1)
    print(f"Found {len(image_paths)} image(s) to convert")

    # Prepare command-line arguments
    bf2raw_args = []
    if args.progress: bf2raw_args.append('-p')
    if args.tile_width: bf2raw_args.extend(['--tile-width', str(args.tile_width)])
    if args.tile_height: bf2raw_args.extend(['--tile-height', str(args.tile_height)])
    if args.resolutions: bf2raw_args.extend(['--resolutions', str(args.resolutions)])
    if args.compression: bf2raw_args.extend(['--compression', args.compression])
    if args.max_workers: bf2raw_args.extend(['--max-workers', str(args.max_workers)])
    if args.series: bf2raw_args.extend(['--series', args.series])
    if args.no_minmax: bf2raw_args.append('--no-minmax')
    if args.memo_directory: bf2raw_args.extend(['--memo-directory', args.memo_directory])
    if args.downsample_type: bf2raw_args.extend(['--downsample-type', args.downsample_type])
    if args.overwrite: bf2raw_args.append('--overwrite')
    if args.debug: bf2raw_args.extend(['--log-level', 'DEBUG'])

    raw2ometiff_args = []
    if args.progress: raw2ometiff_args.append('-p')
    raw2ometiff_args.extend(['--compression', args.ometiff_compression])
    if args.ometiff_quality: raw2ometiff_args.extend(['--quality', str(args.ometiff_quality)])
    if args.rgb: raw2ometiff_args.append('--rgb')
    if args.split: raw2ometiff_args.append('--split')
    if args.split_planes: raw2ometiff_args.append('--split-planes')
    if args.debug: raw2ometiff_args.extend(['--log-level', 'DEBUG'])

    success_count = 0
    for image_path in image_paths:
        rel_path = os.path.relpath(image_path, input_dir)
        output_subdir = os.path.join(args.output_dir, os.path.dirname(rel_path))
        os.makedirs(output_subdir, exist_ok=True)
        if convert_image(image_path, output_subdir, bf2raw_args, raw2ometiff_args, args.keep_zarr, args.overwrite):
            success_count += 1

    print(f"Successfully converted {success_count}/{len(image_paths)} images.")
    if success_count < len(image_paths):
        sys.exit(1)

if __name__ == "__main__":
    main()
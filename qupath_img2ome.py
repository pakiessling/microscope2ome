#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Union

def convert_image(
    input_path: str,
    output_path: str,
    crop: Optional[str] = None,
    zslices: Optional[str] = None,
    timepoints: Optional[str] = None,
    downsample: float = 1.0,
    pyramid_scale: float = 1.0,
    big_tiff: Optional[bool] = None,
    tile_size: Optional[int] = None,
    tile_width: int = 512,
    tile_height: int = 512,
    compression: Optional[str] = None,
    parallelize: bool = True,
    overwrite: bool = False,
    series: Optional[int] = None,
):
    """
    Convert a single image using QuPath convert-ome
    
    Args:
        input_path: Path to the input image
        output_path: Path for the output file (.ome.tiff or .ome.zarr)
        crop: Bounding box in format "x,y,w,h"
        zslices: Z-slices to export ("all", a number, or a range like "1-5")
        timepoints: Timepoints to export ("all", a number, or a range like "1-5")
        downsample: Downsample factor
        pyramid_scale: Scale factor for pyramidal images
        big_tiff: Force big TIFF format
        tile_size: Tile size (equal height and width)
        tile_width: Tile width
        tile_height: Tile height
        compression: Compression type for TIFF files
        parallelize: Whether to parallelize tile export
        overwrite: Whether to overwrite existing files
        series: Series number for Bio-Formats
        
    Returns:
        True if conversion was successful, False otherwise
    """
    cmd = ["QuPath", "convert-ome"]
    
    # Add optional arguments if provided
    if crop:
        cmd.extend(["-r", crop])
    if zslices:
        cmd.extend(["-z", zslices])
    if timepoints:
        cmd.extend(["-t", timepoints])
    if downsample != 1.0:
        cmd.extend(["-d", str(downsample)])
    if pyramid_scale > 1.0:
        cmd.extend(["-y", str(pyramid_scale)])
    if big_tiff is not None:
        cmd.append("--big-tiff" if big_tiff else "--big-tiff=false")
    if tile_size is not None:
        cmd.extend(["--tile-size", str(tile_size)])
    if tile_width != 512:
        cmd.extend(["--tile-width", str(tile_width)])
    if tile_height != 512:
        cmd.extend(["--tile-height", str(tile_height)])
    if compression:
        cmd.extend(["-c", compression])
    if not parallelize:
        cmd.append("--no-parallelize")
    if overwrite:
        cmd.append("--overwrite")
    if series is not None:
        cmd.extend(["--series", str(series)])
    
    # Add the required arguments (input and output paths)
    cmd.extend([input_path, output_path])
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Successfully converted {input_path} to {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error converting {input_path}: {e.stderr}")
        return False

def process_directory(
    input_dir: str,
    output_dir: str,
    output_format: str,
    extensions: List[str],
    **kwargs,
):
    """
    Process all files with matching extensions in a directory
    
    Args:
        input_dir: Directory containing input images
        output_dir: Directory for output files
        output_format: Either 'tiff' or 'zarr'
        extensions: List of file extensions to process
        **kwargs: Additional arguments to pass to convert_image
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get all files in input directory with matching extensions
    files = []
    for ext in extensions:
        files.extend(list(input_path.glob(f"*{ext}")))
    
    if not files:
        print(f"No files with extensions {extensions} found in {input_dir}")
        return
    
    # Process each file
    success_count = 0
    for file in files:
        if output_format == 'tiff':
            output_file = output_path / f"{file.stem}.ome.tiff"
        else:
            output_file = output_path / f"{file.stem}.ome.zarr"
        
        if convert_image(str(file), str(output_file), **kwargs):
            success_count += 1
    
    print(f"Successfully converted {success_count} of {len(files)} files")

def main():
    parser = argparse.ArgumentParser(
        description="Wrapper for QuPath convert-ome that handles both single images and directories"
    )
    
    # Required arguments
    parser.add_argument("input", help="Input image file or directory")
    parser.add_argument(
        "output", 
        help="Output file (for single image) or directory (for input directory)"
    )
    
    # Format selection
    parser.add_argument(
        "--format", 
        choices=["tiff", "zarr"], 
        default="tiff",
        help="Output format (tiff or zarr), only used for directory input"
    )
    
    # File extensions for directory processing
    parser.add_argument(
        "--extensions", 
        nargs="+", 
        default=[".tif", ".tiff", ".svs", ".ndpi", ".jpg", ".jpeg", ".png",".czi"],
        help="File extensions to process when input is a directory"
    )
    
    # Optional arguments from QuPath convert-ome
    parser.add_argument("-r", "--crop", help="Bounding box in format 'x,y,w,h'")
    parser.add_argument(
        "-z", "--zslices", 
        help="Z-slices to export ('all', a number, or a range like '1-5')"
    )
    parser.add_argument(
        "-t", "--timepoints", 
        help="Timepoints to export ('all', a number, or a range like '1-5')"
    )
    parser.add_argument(
        "-d", "--downsample", 
        type=float, 
        default=1.0,
        help="Downsample factor"
    )
    parser.add_argument(
        "-y", "--pyramid-scale", 
        type=float, 
        default=1.0,
        help="Scale factor for pyramidal images"
    )
    parser.add_argument(
        "--big-tiff", 
        action="store_true", 
        default=None,
        help="Force big TIFF format"
    )
    parser.add_argument(
        "--no-big-tiff", 
        dest="big_tiff", 
        action="store_false",
        help="Force non-big TIFF format"
    )
    parser.add_argument(
        "--tile-size",
        type=int,
        help="Tile size (equal height and width)"
    )
    parser.add_argument(
        "--tile-width",
        type=int,
        default=512,
        help="Tile width (default=512)"
    )
    parser.add_argument(
        "--tile-height",
        type=int,
        default=512,
        help="Tile height (default=512)"
    )
    parser.add_argument(
        "-c", "--compression",
        choices=["UNCOMPRESSED", "DEFAULT", "JPEG", "J2K", "J2K_LOSSY", "LZW", "ZLIB"],
        help="Compression type for TIFF files"
    )
    parser.add_argument(
        "-p", "--parallelize",
        action="store_true",
        default=True,
        help="Parallelize tile export if possible"
    )
    parser.add_argument(
        "--no-parallelize",
        dest="parallelize",
        action="store_false",
        help="Don't parallelize tile export"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files"
    )
    parser.add_argument(
        "--series",
        type=int,
        help="Series number for Bio-Formats"
    )
    
    args = parser.parse_args()
    
    # Check if input is a file or directory
    input_path = Path(args.input)
    
    # Handle file vs directory
    if input_path.is_file():
        # For single file: ensure output has correct extension
        output_path = args.output
        if not (output_path.endswith(".ome.tiff") or output_path.endswith(".ome.zarr")):
            if args.format == "tiff":
                output_path = f"{output_path}.ome.tiff"
            else:
                output_path = f"{output_path}.ome.zarr"
                
        # Process single file
        convert_image(
            str(input_path),
            output_path,
            crop=args.crop,
            zslices=args.zslices,
            timepoints=args.timepoints,
            downsample=args.downsample,
            pyramid_scale=args.pyramid_scale,
            big_tiff=args.big_tiff,
            tile_size=args.tile_size,
            tile_width=args.tile_width,
            tile_height=args.tile_height,
            compression=args.compression,
            parallelize=args.parallelize,
            overwrite=args.overwrite,
            series=args.series,
        )
    
    elif input_path.is_dir():
        # Process directory
        kwargs = {
            'crop': args.crop,
            'zslices': args.zslices,
            'timepoints': args.timepoints,
            'downsample': args.downsample,
            'pyramid_scale': args.pyramid_scale,
            'big_tiff': args.big_tiff, 
            'tile_size': args.tile_size,
            'tile_width': args.tile_width,
            'tile_height': args.tile_height,
            'compression': args.compression,
            'parallelize': args.parallelize,
            'overwrite': args.overwrite,
            'series': args.series,
        }
        
        process_directory(
            str(input_path),
            args.output,
            args.format,
            args.extensions,
            **kwargs
        )
    
    else:
        print(f"Error: Input path '{args.input}' does not exist")
        sys.exit(1)

if __name__ == "__main__":
    main()
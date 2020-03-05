#!/usr/bin/env python3

# Copyright 2020 Robert Bragg robert@sixbynine.org
# Copyright 2018 Kalle qalle85@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Original source:
# https://github.com/play3577/nes-chr-decode

import argparse
import os.path
import png
import sys

CHAR_WIDTH = 8  # character width in pixels
CHAR_HEIGHT = 8  # character height in pixels
BYTES_PER_CHAR = 16  # bytes per character in CHR data
CHARS_PER_ROW = 16  # characters per row in output image

DEFAULT_PALETTE = ("000000", "555555", "aaaaaa", "ffffff")

def decode_color_code(color):
    """Decode an HTML color code (6 hexadecimal digits)."""

    try:
        if len(color) != 6:
            raise ValueError
        color = int(color, 16)
    except ValueError:
        exit("Error: invalid color code.")
    red = color >> 16
    green = (color >> 8) & 0xff
    blue = color & 0xff
    return (red, green, blue)

def parse_arguments():
    """Parse command line arguments using argparse."""

    parser = argparse.ArgumentParser(description='Converts an NES CHR (graphics) data file to a PNG file.')
    parser.add_argument('--color0',
                        default=DEFAULT_PALETTE[0],
                        help='What color in the PNG image should correspond to color 0 in the CHR data.')
    parser.add_argument('--color1',
                        default=DEFAULT_PALETTE[1],
                        help='What color in the PNG image should correspond to color 1 in the CHR data.')
    parser.add_argument('--color2',
                        default=DEFAULT_PALETTE[2],
                        help='What color in the PNG image should correspond to color 2 in the CHR data.')
    parser.add_argument('--color3',
                        default=DEFAULT_PALETTE[3],
                        help='What color in the PNG image should correspond to color 3 in the CHR data.')
    parser.add_argument('input_file',
                        help='The PNG image file to read')
    parser.add_argument('output_file',
                        help='The NES CHR data file to write')

    args = parser.parse_args()

    # colors
    color0 = decode_color_code(args.color0)
    color1 = decode_color_code(args.color1)
    color2 = decode_color_code(args.color2)
    color3 = decode_color_code(args.color3)

    # source file
    source = args.input_file
    if not os.path.isfile(source):
        exit("Error: the input file does not exist.")
    try:
        size = os.path.getsize(source)
    except OSError:
        exit("Error getting input file size.")
    (charRowCount, remainder) = divmod(size, CHARS_PER_ROW * BYTES_PER_CHAR)
    if charRowCount == 0 or remainder:
        exit("Error: invalid input file size.")

    # target file
    target = args.output_file
    if os.path.exists(target):
        exit("Error: the output file already exists.")
    dir = os.path.dirname(target)
    if dir != "" and not os.path.isdir(dir):
        exit("Error: the output directory does not exist.")

    return {
        "palette": (color0, color1, color2, color3),
        "source": source,
        "target": target,
    }

def generate_character_rows(source):
    """Yield one character row of CHR data per call."""

    size = source.seek(0, 2)
    source.seek(0)
    while source.tell() < size:
        yield source.read(CHARS_PER_ROW * BYTES_PER_CHAR)

def decode_character_slice(loByte, hiByte):
    """Decode one pixel row of one character."""

    # the data is planar; decode least significant bits first
    pixels = []
    for x in range(CHAR_WIDTH):
        pixels.append((loByte & 1) | ((hiByte & 1) << 1))
        loByte >>= 1
        hiByte >>= 1
    # return the pixels in correct order
    return reversed(pixels)

def generate_pixel_rows(source, settings):
    """Generate PNG pixel rows from the CHR data file."""

    pixels = []  # the pixel row to yield
    for chrData in generate_character_rows(source):  # character rows
        for pixelY in range(CHAR_HEIGHT):  # pixel rows
            pixels.clear()
            for charX in range(CHARS_PER_ROW):  # characters
                # get low and high byte of current character slice
                chrDataIndex = charX * BYTES_PER_CHAR + pixelY
                loByte = chrData[chrDataIndex]
                hiByte = chrData[chrDataIndex + 8]
                # decode slice and add to pixel row
                pixels.extend(decode_character_slice(loByte, hiByte))
            yield pixels

def main():
    settings = parse_arguments()

    sourceSize = os.path.getsize(settings["source"])
    charRowCount = sourceSize // (CHARS_PER_ROW * BYTES_PER_CHAR)
    width = CHARS_PER_ROW * CHAR_WIDTH
    height = charRowCount * CHAR_HEIGHT
    palette = ((0,0,0), (255,0,0), (255,128,0), (255,255,255))

    targetImage = png.Writer(
        width=width,
        height=height,
        bitdepth=2,  # 4 colors
        palette=settings["palette"],
        compression=9  # maximum
    )

    with open(settings["source"], "rb") as source, \
    open(settings["target"], "wb") as target:
        targetRows = generate_pixel_rows(source, settings)
        targetImage.write(target, targetRows)

if __name__ == "__main__":
    main()

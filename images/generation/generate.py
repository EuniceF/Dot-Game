"""Set of utility functions for generating images for Dots & Co game to use in place of canvas shapes

Depends on ImageMagick 6.8
`convert` must be in path
http://www.imagemagick.org

Notes:
    Point generation logic is re-run for each shape, colour combination, but is independent of colour
    This isn't really a problem for a small number of colours & shapes, but is repeating computation needlessly
    Solution would be to memoise point/shape generating functions, such as get_beam_points
"""

# TODO: add docstrings
#pylint: skip-file

import subprocess
import math
import os
from itertools import starmap
from operator import mul
from enum import Enum

from view import GridView

__author__ = "Benjamin Martin"
__copyright__ = "Copyright 2017, The University of Queensland"
__license__ = "MIT"
__date__ = "27/09/2017"
__version__ = "1.1.2"

# https://en.wikipedia.org/wiki/Rotation_matrix
ROTATION_0 = [[1, 0],
              [0, 1]]

ROTATION_90 = [[0, -1],
               [1, 0]]

ROTATION_180 = [[-1, 0],
                [0, -1]]

ROTATION_270 = [[0, 1],
                [-1, 0]]


# https://stackoverflow.com/a/45159105
def matrix_multiply(matrix1, matrix2):
    return [[sum(starmap(mul, zip(row, col))) for col in zip(*matrix2)] for row in matrix1]


def matrix_transpose(matrix):
    return list(zip(*matrix))


def get_circle_shape(size):
    width, height = size
    centre_x, centre_y = width // 2, height // 2
    return f"'circle {centre_x},{centre_y} {centre_x},1'"


def get_equilateral_triangle_shape(size):
    width, height = size
    centre_x, centre_y = width // 2, height // 2

    triangle_height = height * math.sin(math.pi // 3)
    triangle_top = (height - triangle_height) // 2
    triangle_bottom = (height + triangle_height) // 2

    return f'"path \'M {centre_x},{triangle_top}  L 0,{triangle_bottom}  L {width},{triangle_bottom} L {centre_x},{triangle_top} Z\' "'


def get_square_shape(size, offset=(0, 0)):
    offset_x, offset_y = offset
    width, height = size
    left, top = offset_x, offset_y
    right, bottom = width - offset_x, height - offset_y

    return get_path_from_points(((left, top), (right, top), (right, bottom), (left, bottom), (left, top)))

    # return f'"path \'M {left},{top}  L {right},{top}  L {right},{bottom}  L {left},{bottom} L {left},{top} Z\' "'


def get_path_from_points(points):
    path = "  L ".join(f"{p[0]},{p[1]}" for p in points)
    return f'"path \'M {path} Z\' "'



def generate_shape(shape, colour, file_path, size=(128, 128), ext='.png'):
    width, height = size
    return f"convert -size {width}x{height} canvas:none -fill {colour!r} -draw {shape} {file_path}{ext}"


def generate_basic(colour, file_path, size=(128, 128), ext='.png'):
    return generate_shape(get_circle_shape(size), colour, file_path, size=size, ext=ext)


def generate_swirl(colour, file_path, size=(128, 128), ext='.png'):
    # swirl-overlay.png will be resized to match 'size'
    width, height = size
    shape = get_circle_shape(size)
    overlay_path = os.path.abspath('swirl-overlay.png')
    return f"convert -size {width}x{height} canvas:none -fill {colour!r} -draw {shape} \\( {overlay_path} -normalize +level 75% -resize {width}x{height} \\) -compose screen -composite {file_path}{ext}"


def generate_flower(colour, file_path, size=(128, 128), ext='.png'):
    width, height = size
    shape = get_circle_shape(size)
    mask_path = os.path.abspath('flower-mask.png')
    square = get_square_shape(size)
    return f"convert \\( -size {width}x{height} canvas:none -fill {colour!r} -draw {square} \\) -alpha on \\( +clone -channel a -fx 0 \\) +swap \\( {mask_path} -resize {width}x{height} \\) -composite {file_path}{ext}"


def generate_companion(colour, file_path, size=(128, 128), ext='.png'):
    return generate_shape(get_equilateral_triangle_shape(size), colour, file_path, size=size, ext=ext)


def generate_square(colour, file_path, size=(128, 128), ext='.png'):
    return generate_shape(get_square_shape(size, offset=(5, 5)), colour, file_path, size=size, ext=ext)


class Orientations(Enum):
    X = 'x'
    Y = 'y'
    XY = 'xy'


ROTATIONS = {
    Orientations.X: [ROTATION_90, ROTATION_270],
    Orientations.Y: [ROTATION_0, ROTATION_180],
    Orientations.XY: [ROTATION_0, ROTATION_90, ROTATION_180, ROTATION_270],
}


def get_beam_points(size, orientation):
    width, height = size
    centre = width // 2, height // 2
    head_height = int(height * .2)
    # head_width = int(head_height / math.sin(math.pi/3))  # equilateral head
    head_width = int(head_height * 2)
    stem_width, stem_height = int(width * .15), int(height * .3)

    points = [
        (stem_width // 2, stem_width // 2),
        (stem_width // 2, int(stem_height * .75)),
        (head_width // 2, stem_height),
        (0, stem_height + head_height),
    ]

    for i in range(2, -1, -1):
        x, y = points[i]
        points.append((-x, y))

    rotations = ROTATIONS[orientation]

    all_points = []

    rotate_point = lambda rotation, point: matrix_transpose(matrix_multiply(rotation, matrix_transpose((point,))))[0]

    for rotation in rotations:
        rotated_points = [rotate_point(rotation, p) for p in points]
        all_points.extend(rotated_points)

    # offset to centre
    return [tuple(a + b for a, b in zip(p, centre)) for p in all_points]


def generate_beam(colour, file_path, orientation, size=(128, 128), ext='.png'):
    all_points = get_beam_points(size, orientation)

    return generate_shape(get_path_from_points(all_points), colour, file_path, size=size,
                          ext=ext)


def generate_images(colours, cwd='./output'):
    """Generates images for Dots & Co based upon colour sets
    
    Parameters:
        colours (dict<*, str>): Dictionary of names => colours
    """

    # Only use one colour
    # colours = {key: colours[key] for key in [1]}

    del colours[None]
    del colours['blank']

    images = [
        ('basic', generate_basic, colours, ()),
        ('companion', generate_companion, colours, ()),
        ('swirl', generate_swirl, colours, ()),
        ('flower', generate_flower, colours, ()),
        ('beam/x', generate_beam, colours, (Orientations.X,)),
        ('beam/y', generate_beam, colours, (Orientations.Y,)),
        ('beam/xy', generate_beam, colours, (Orientations.XY,)),
    ]

    static = [
        'anchor/anchor.png',
        'balloon/balloon.png',
        'butterfly/coocoon.png',
        'butterfly/coocoon-cracked.png',
        'butterfly/butterfly-0.png',
        'butterfly/butterfly-1.png',
        'butterfly/butterfly-2.png',
        'turtle/shell.png',
        'turtle/turtle.png',
        'wildcard/wildcard.png',
    ]

    sizes = [
        (128, 128),
        (40, 40),
        (20, 20)
    ]

    exts = ['.png', '.gif']

    for size in sizes:

        for ext in exts:

            size_prefix = f"{size[0]}x{size[1]}"

            # dynamic
            for dot_prefix, generator, colours, args in images:

                prefix = os.path.join(size_prefix, dot_prefix)

                os.makedirs(os.path.join(cwd, prefix), exist_ok=True)

                if colours is not None:
                    for name, colour in colours.items():
                        cmds = generator(colour, f'{prefix}/{name}', *args, size=size, ext=ext)

                        if isinstance(cmds, str):
                            cmds = [cmds]

                        for cmd in cmds:
                            print(cmd)
                            subprocess.run(cmd, shell=True, cwd=cwd)

            # static
            for path in static:
                input = os.path.abspath(os.path.join('static', path))
                output_file = os.path.splitext(path)[0] + ext
                output = os.path.join(size_prefix, output_file)

                os.makedirs(os.path.join(cwd, os.path.dirname(output)), exist_ok=True)

                cmd = f'convert {input} -resize {size_prefix} {output}'

                print(cmd)
                subprocess.run(cmd, shell=True, cwd=cwd)


def main():
    """Main function"""
    generate_images(GridView.COLOURS, cwd='../dots')


if __name__ == '__main__':
    main()

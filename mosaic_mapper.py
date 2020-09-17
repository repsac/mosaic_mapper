import os
import enum
import math
import numpy
import string
import tempfile
import argparse
from PIL import Image, ImageChops


GRID_SIZE = (10, 10)


class ValidationError(Exception):
    pass


def run(image_path,
        grid_size=None,
        destination=None,
        validate=False):
    data = {
        'grid_size': grid_size or GRID_SIZE
    }

    destination = destination or os.getcwd()

    data.update(_parse_image(image_path))
    report = _build_output(data)

    basename = os.path.splitext(os.path.basename(image_path))[0]
    destination = os.path.join(destination, basename)
    out_report = _dump_report(report, destination)

    if validate:
        _validate(report, image_path)

    return (out_report, report)


def rebuild_image(data, output_image):
    pixel_array = [None] * data['image_size'][1]
    pixel_array = [[] for x in pixel_array]
    row_index = 0
    row_offset = 0
    index = 0

    grid_area = data['grid_size'][0]*data['grid_size'][1]
    grid_count = 0

    grid_row_area = int(grid_area * (data['image_size'][0] / 
                                     data['grid_size'][0]))

    for grid in data['grids']:

        pixels = data['grids'][grid]['pixels']
        grid_index = 1

        if index == grid_row_area:
            index = 0
            row_index = 0
            yoffset = int(len(pixels) / data['grid_size'][1])
            grid_area = data['grid_size'][0]*yoffset
            row_offset += data['grid_size'][1]

        for pixel in pixels:

            try:
                pixel_array[row_index+row_offset].append(pixels[pixel])
            except IndexError:
                break

            if grid_index == data['grid_size'][0]:
                grid_index = 1
                row_index += 1
            else:
                grid_index += 1

            grid_count += 1
            index += 1

        if grid_count == grid_area:
            grid_count = 0
            row_index = 0

    generate_image(output_image, pixel_array)
    return os.path.exists(output_image)


def generate_image(image_path, pixel_array):
    array = numpy.array(pixel_array, dtype=numpy.uint8)
    image = Image.fromarray(array)
    image.save(image_path)


def hex2rgb(hex):
    hex = hex.lstrip('#')
    return tuple(int(hex[i:i+2], 16) for i in (0, 2, 4))


def rgb2hex(rgb):

    def clamp(x):
        return max(0, min(x, 255))

    return '#{0:02x}{1:02x}{2:02x}'.format(
        clamp(rgb[0]),
        clamp(rgb[1]),
        clamp(rgb[2])
    )


def _dump_report(report, destination):
    out_report = '{}.txt'.format(destination)
    tab = '  '

    txt = "TOTAL COLORS:"
    for index, color in enumerate(report['colors']):
        txt += "\n{}RGB{} = {}".format(
            tab, color,
            report['color_counts'][index])

    txt += "\n\nGRIDS:"
    for grid in report['grids']:
        txt += "\n{}{}".format(tab,grid)
        pixels = report['grids'][grid]['pixels']

        txt += "\n{}Total Colors In Grid:".format(tab*2)
        for index, color in enumerate(report['grids'][grid]['colors']):
            txt += "\n{}RGB{} = {}".format(
                tab*3, color,
                report['grids'][grid]['color_counts'][index])
        
        txt += "\n{}Mapping:".format(tab*2)
        for index, pxl in enumerate(pixels):
            txt += "\n{}{}={}".format(tab*3, pxl, pixels[pxl])
    with open(out_report, 'w') as f:
        f.write(txt)
    return out_report


def _validate(report, image_path):
    ext = os.path.splitext(image_path)[-1]
    tmpimg = tempfile.mktemp(suffix=ext)

    if not rebuild_image(report, tmpimg):
        raise ValidationError("Validation image not on disk")

    try:
        _compare_images(image_path, tmpimg)
    finally:
        if os.path.exists(tmpimg):
            os.remove(tmpimg)


def _compare_images(image0, image1):
    try:
        ImageChops.difference(Image.open(image0),
                              Image.open(image1))
    except ValueError:
        error = "Image do not match {} != {}".format(
            image0, image1)
        raise ValidationError(error)


def _parse_image(image_path):
    with Image.open(image_path) as img_data:
        data = {
            'size': img_data.size,
            'pixel_colors': img_data.getdata()
        }
    return data


def _prefix_char(index):
    mult = int(index / (len(string.ascii_uppercase)-1))
    index = index - (mult*index)
    mult += 1
    return string.ascii_uppercase[index]*mult


def _build_output(data):
    colors = []
    color_counts = []
    grids = {}

    row = 0
    grid_row = 0
    grid_column = 1
    grid_index = 0
    iter_grid = data['grid_size'][1]*data['size'][0]

    def update_col_count(x, y, z):
        try:
            i = x.index(z)
            y[i] += 1
        except ValueError:
            x.append(z)
            y.append(1)

    for index, pcol in enumerate(data['pixel_colors']):

        pcol = pcol
        update_col_count(colors, color_counts, pcol)

        if index % iter_grid == 0:
            grid_row += 1
            row = 0

        if index % data['size'][0] == 0:
            row += 1
            grid_index = 0

        grid_id = '{}{}'.format(_prefix_char(grid_index), grid_row)
        pixel = '{}:{}'.format(grid_column, row)

        grid_data = grids.setdefault(grid_id,
        {
            'colors': [],
            'color_counts': [],
            'pixels': {}
        })
        update_col_count(grid_data['colors'],
                         grid_data['color_counts'],
                         pcol)
        grid_data['pixels'][pixel] = pcol

        if grid_column % data['grid_size'][0] == 0:
            grid_column = 1
            grid_index += 1
        else:
            grid_column += 1
    
    report = {
        'colors': colors,
        'color_counts': color_counts,
        'grids': grids,
        'image_size': data['size'],
        'grid_size': data['grid_size']
    }
    return report


def _args(image_nargs=None,
          grid_size='10x10',
          destination=os.getcwd()):
    parser = argparse.ArgumentParser()
    parser.add_argument('image', nargs=image_nargs)
    parser.add_argument('-d', '--destination',
                        default=destination)
    parser.add_argument('-g', '--grid',
                        default=grid_size)

    args = vars(parser.parse_args())
    args['grid'] = args['grid'].split('x')
    args['grid'] = (int(args['grid'][0]), int(args['grid'][1]))
    return args


def _main():
    args = _args()
    run(args['image'], 
        grid_size=args['grid'],
        destination=args['destination'])
    

if __name__ == '__main__':
    _main()

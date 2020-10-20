import os
import enum
import math
import numpy
import string
import tempfile
import argparse
from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageOps
)


GRID_SIZE = (10, 10)
PIXEL_RES = 98
PIXEL_FONT_FACE = 'arial.ttf'
PIXEL_FONT_SIZE = 10

GRID_MAP = {
    'size': PIXEL_RES,
    'border': 1
}


def run(image_path,
        grid_size=None,
        destination=None,
        validate_only=False):
    grid_size = grid_size or GRID_SIZE
    destination = destination or os.getcwd()
    basename = os.path.splitext(os.path.basename(image_path))[0]
    destination = os.path.join(destination, basename)

    size, pixel_data = _load_image(image_path)
    grids = _build_grids(size, pixel_data, grid_size)

    _validate_grid(grids, image_path)
    mapped_colors = {}

    if not validate_only:
        mapped_colors = _map_colors(grids)
        _write_csv(grids, mapped_colors, destination)
        _create_grid_map(GRID_MAP.copy(), grids, mapped_colors, destination)

    return {
        'grids': grids,
        'mapped_colors': mapped_colors
    }


def generate_image(img_path, pixel_array):
    array = numpy.array(pixel_array, dtype=numpy.uint8)
    image = Image.fromarray(array)
    image.save(img_path)


def rebuild_from_grids(grids, image_path):
    pixel_array = convert_grid_to_pixel_array(grids)
    generate_image(image_path, pixel_array)
    return os.path.exists(image_path)


def convert_grid_to_pixel_array(grids):
    pixel_array = []
    grid_row_offset = 0

    for grid_row in grids:
        for grid in grid_row:
            for index, pixel_row in enumerate(grid):
                try:
                    ia_row = pixel_array[index+grid_row_offset]
                except IndexError:
                    ia_row = []
                    pixel_array.append(ia_row)
                ia_row.extend(pixel_row)
        grid_row_offset += len(grid)

    return pixel_array


def _create_grid_map(settings, grids, mapped_colors, destination):

    def invert_hue(x):
        return (
        int(x[0] + 179 if x[0] < 179 else x[0] - 179),
        int(x[1] + 179 if x[1] < 179 else x[1] - 179),
        int(x[2] + 179 if x[2] < 179 else x[2] - 179)
    )

    res = (settings['size'], settings['size'])
    font = ImageFont.truetype(PIXEL_FONT_FACE, PIXEL_FONT_SIZE)

    def compile_images(image_array):
        width = 0
        height = 0
        positions = []

        for image_row in image_array:

            width = 0
            for im in image_row:
                positions.append((im, (width, height)))
                width += im.size[0]

            height += im.size[1]

        new_img = Image.new('RGB', (width, height))

        for pos in positions:
            new_img.paste(im=pos[0], box=pos[1])
        
        return new_img

    grid_images = []
    for gri, grid_row in enumerate(grids):
        grid_images.append([])
        for gi, grid in enumerate(grid_row):
            grid_id = "{}{}".format(_prefix_char(gi), gri+1)
            grid_array = []
            for pri, pixel_row in enumerate(grid):
                grid_array.append([])
                for pi, pixel in enumerate(pixel_row):
                    pixel_id = "{}:{}".format(pi+1, pri+1)
                    image = Image.new("RGB", res, pixel)
                    draw = ImageDraw.Draw(image)

                    height = 0
                    text = []
                    label = "{}={}".format(grid_id, pixel_id)

                    color_id = mapped_colors['colors'][str(pixel)]['id']
                    for each in (label, color_id):
                        size = font.getsize(each)
                        height += size[1]
                        text.append((each, 
                                    (res[0] / 2) - (size[0] / 2),
                                    size[1]))
                    
                    height = (height / len(text))
                    inverted = invert_hue(pixel)
                    for t,x,y in text:
                        height += y
                        draw.text((x, 
                                   height+y), 
                                   t, 
                                   inverted, 
                                   font=font)
                    grid_array[-1].append(ImageOps.expand(
                        image, border=settings['border'], fill=inverted))

            grid_images[-1].append(compile_images(grid_array))
            fname = "{}_GRID-{}.png".format(destination, grid_id)
            grid_images[-1][-1].save(fname)
    
    bordered = []
    for grid_row in grid_images:
        bordered.append([])
        for grid in grid_row:
            bordered[-1].append(ImageOps.expand(
                grid, border=10, fill=(0, 0, 0)))

    compiled_grid = compile_images(bordered)
    fname = "{}_GRID-COMPLETE.png".format(destination)
    compiled_grid.save(fname)


def _prefix_char(index):
    mult = int(index / (len(string.ascii_uppercase)))
    index = index - (mult*len(string.ascii_uppercase))
    mult += 1
    return string.ascii_uppercase[index]*mult


def _write_csv(grids, mapped_colors, destination):

    rows = ['COLOR ID, RGB, COUNT']
    for color in mapped_colors['colors']:
        row = [mapped_colors['colors'][color]['id'],
               '"{}"'.format(color[1:-1]), 
               str(mapped_colors['colors'][color]['count'])]
        rows.append(','.join(row))

    csv_fi = '{}_COLOR-COUNT.csv'.format(destination)

    with open(csv_fi, 'w') as x:
        x.write('\n'.join(rows))

    def insert_row(new_row, array):

        for x in range(len(array[-1]) - len(new_row)): 
            new_row.append('')

        array.insert(0, ','.join(new_row))

    for gri, grid_row in enumerate(grids):
        for gi, grid in enumerate(grid_row):
            grid_txt = []
            for row in grid:
                row_txt = []
                for pxl in row:
                    str_pxl = str(pxl)
                    color_id = mapped_colors['colors'][str_pxl]['id']
                    row_txt.append('{}'.format(color_id))
                grid_txt.append(','.join(row_txt))

            grid_prefix = _prefix_char(gi)
            grid_key = '{}{}'.format(grid_prefix, gri+1)

            insert_row(["MAPPING"], grid_txt)
            insert_row([], grid_txt)
            for color in mapped_colors['grid_count'][grid_key]:
                id = mapped_colors['colors'][color]['id']

                new_row = [id, 
                           str(mapped_colors['grid_count'][grid_key][color])]
                insert_row(new_row, grid_txt)

            insert_row(["COUNT"], grid_txt)

            csv_fi = '{}_GRID-{}.csv'.format(destination, grid_key)

            with open(csv_fi, 'w') as x:
                x.write('\n'.join(grid_txt))
 

def _validate_grid(grids, image_path):
    ext = os.path.splitext(image_path)[-1]
    tmpimg = tempfile.mktemp(suffix=ext)

    if not rebuild_from_grids(grids, tmpimg):
        raise IOError("Validation image not on disk")

    try:
        _compare_images(image_path, tmpimg)
    finally:
        if os.path.exists(tmpimg):
            os.remove(tmpimg)


def _compare_images(image0, image1):

    with Image.open(image0) as img_data:
        im0_size = img_data.size
        im0_data = img_data.getdata()
    
    with Image.open(image1) as img_data:
        im1_size = img_data.size
        im1_data = img_data.getdata()
    
    if im0_size != im1_size:
        error = "Image sizes do not match {} != {}".format(
            im0_size, im1_size)
        raise IOError(error)

    for i, (x, y) in enumerate(zip(im0_data, im1_data)):
        x = _strip_apha(x)
        y = _strip_apha(y)
        if x != y:
            error = "Pixel {} colors do not match {} != {}".format(i, x, y)
            raise IOError(error)


def _map_colors(grids):
    mapped_colors = {
        'colors': {},
        'grid_count': {}
    }

    colors = mapped_colors['colors']
    grid_count = mapped_colors['grid_count']

    for gri, grid_row in enumerate(grids):

        grid_prefix = _prefix_char(gri)

        for gi, grid in enumerate(grid_row):

            grid_prefix = _prefix_char(gi)
            grid_key = '{}{}'.format(grid_prefix, gri+1)

            if grid_key not in grid_count:
                grid_count[grid_key] = {}

            for row in grid:

                for color in row:
    
                    str_color = str(color)

                    if str_color not in grid_count[grid_key]:
                        grid_count[grid_key][str_color] = 0
                
                    grid_count[grid_key][str_color] += 1

                    if str_color not in colors:
                        colors[str_color] = {
                            'color': color,
                            'count': 0
                        }

                    colors[str_color]['count'] += 1

    for index, color in enumerate(colors):
        colors[color]['id'] = 'Color:{}'.format(_prefix_char(index))

    return mapped_colors


def _strip_apha(color):
    return color[:3] if len(color) == 4 else color


def _build_grids(size, pixel_data, grid_size):

    iter_grid = grid_size[1] * size[0]
    grid_limit = grid_size[0] * grid_size[1]

    grid_split = math.ceil(iter_grid / grid_limit)
    grid_y_count = math.ceil(size[1] / grid_size[1])

    last_grid_row = grid_size[1] - ((grid_size[1] * grid_y_count) - size[1])

    grids = []
    for x in range(grid_y_count):
        grids.append([])
    for x, grid_row in enumerate(grids):
        val = last_grid_row if x == grid_y_count-1 else grid_size[1]
        for y in range(grid_split):
            grid_row.append([])
            for i in range(val):
                grid_row[-1].append([])

    grid_index = -1
    pixel_row = -1
    grid_row_index = -1

    for index, pcolor in enumerate(pixel_data):

        if index % iter_grid == 0:
            grid_row_index  += 1

        if index % size[0] == 0:
            pixel_row += 1
            if pixel_row == grid_size[1]:
                pixel_row = 0

        if index % grid_size[0] == 0:
            grid_index += 1
            if grid_index == grid_split:
                grid_index = 0

        pcolor = _strip_apha(pcolor)
        grids[grid_row_index][grid_index][pixel_row].append(pcolor)

    if grid_y_count != len(grids):
        error = "Expected {} grid row(s), found {}".format(
            grid_y_count, len(grids)
        )
        raise RuntimeError(error)

    grid_x_count = math.ceil(size[0] / grid_size[0])

    error = ["\n"]
    for row_index, grid_row in enumerate(grids):

        if grid_x_count != len(grid_row):
            error.append("(Grid Row={}) Expected {} grid(s), found {}".format(
                row_index, grid_x_count, len(grid_row)
            ))

        for grid_index, grid in enumerate(grid_row):
            val = last_grid_row if row_index == grid_y_count-1 else grid_size[1]

            if len(grid) != val:
                error.append("(Grid Row={}, Grid Index={}) Expected {} "\
                    "grid row(s), found {}".format(
                    row_index, grid_index, val, len(grid)
                ))

            for pr_index, pixel_row in enumerate(grid):
                if len(pixel_row) != grid_size[0]:
                    error.append("(Grid Row={}, Grid Index={}, Pixel Row={}) "\
                        "Expected {} pixel row(s), found {}".format(
                        row_index, grid_index, pr_index, grid_size[0], len(pixel_row)
                    ))

    if len(error)>1:
        raise RuntimeError("\n".join(error))

    return grids


def _load_image(image_path):
    with Image.open(image_path) as img_data:
        size = img_data.size
        pixel_data = img_data.getdata()
    return size, pixel_data


def _args(image_nargs=None,
          grid_size='10x10',
          destination=os.getcwd()):
    parser = argparse.ArgumentParser()
    parser.add_argument('image', nargs=image_nargs)
    parser.add_argument('-d', '--destination',
                        default=destination)
    parser.add_argument('-g', '--grid',
                        default=grid_size)
    parser.add_argument('-v', '--validate-only',
                        action='store_true')

    args = vars(parser.parse_args())
    args['grid'] = args['grid'].split('x')
    args['grid'] = (int(args['grid'][0]), int(args['grid'][1]))
    return args


def _main():
    args = _args()
    run(args['image'], 
        grid_size=args['grid'],
        destination=args['destination'],
        validate_only=args['validate-only']) 


if __name__ == '__main__':
    _main()
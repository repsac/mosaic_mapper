import os
import enum
import math
import numpy
import string
import tempfile
import argparse
from PIL import (
    Image,
    ImageChops,
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
        csv=False,
        grid_map=None):
    # init values
    grid_size = grid_size or GRID_SIZE
    destination = destination or os.getcwd()
    basename = os.path.splitext(os.path.basename(image_path))[0]
    destination = os.path.join(destination, basename)

    # parse pixel data
    size, pixel_data = _load_image(image_path)
    grids = _build_grids(size, pixel_data, grid_size)
    count = _count_colors(grids)

    # validate and write to disk
    _validate_grid(grids, image_path)
    if csv:
        _write_csv(grids, count, destination)
    
    #if grid_map is not None:
    settings = GRID_MAP.copy()
    #settings.update(grid_map)
    _create_grid_map(settings, grids, destination)

    return {
        'grids': grids,
        'count': count
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


def _create_grid_map(settings, grids, destination):

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

                    for each in (label, str(pixel)[1:-1]):
                        size = font.getsize(each)
                        height += size[1]
                        text.append((each, 
                                    (res[0] / 2) - (size[0] / 2),
                                    size[1]))
                    
                    height = (height / len(text)) / 2
                    inverted = invert_hue(pixel)
                    for t,x,y in text:
                        height += y
                        draw.text((x, 
                                   height+(y/2)), 
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
    mult = int(index / (len(string.ascii_uppercase)-1))
    index = index - (mult*index)
    mult += 1
    return string.ascii_uppercase[index]*mult


def _write_csv(grids, count, destination):

    def csv_file(path, i1, i2):
        return "{}_Grid-{}{}.csv".format(path, _prefix_char(i1), i2+1)

    for gri, grid_row in enumerate(grids):
        for gi, grid in enumerate(grid_row):
            grid_txt = []
            for row in grid:
                row_txt = []
                for pxl in row:
                    row_txt.append('"{}"'.format(str(pxl)[1:-1]))
                grid_txt.append(','.join(row_txt))

            csv_fi = csv_file(destination, gi, gri)
            with open(csv_fi, 'w') as x:
                x.write('\n'.join(grid_txt))


def _validate_grid(grids, image_path):
    ext = os.path.splitext(image_path)[-1]
    tmpimg = tempfile.mktemp(suffix=ext)
    if not rebuild_from_grids(grids, tmpimg):
        raise IOError("Validation image not on disk")

    import shutil
    shutil.copy(tmpimg, os.path.dirname(image_path))
    try:
        _compare_images(image_path, tmpimg)
    finally:
        if os.path.exists(tmpimg):
            os.remove(tmpimg)


#@TODO: this is NOT working as expected
def _compare_images(image0, image1):
    try:
        ImageChops.difference(Image.open(image0),
                              Image.open(image1))
    except ValueError:
        error = "Image do not match {} != {}".format(
            image0, image1)
        raise IOError(error)


def _count_colors(grids):
    colors = []
    count = []

    def update_count(x, y, z):
        try:
            i = x.index(z)
            y[i] += 1
        except ValueError:
            x.append(z)
            y.append(1)

    for grid_row in grids:
        for grid in grid_row:
            for color in grid:
                update_count(colors, count, color)

    return count


def _build_grids(size, pixel_data, grid_size):

    iter_grid = grid_size[1] * size[0]
    grid_limit = grid_size[0] * grid_size[1]

    grid_split = math.ceil(iter_grid / grid_limit)

    grids = []
    for x in range(grid_split):
        grids.append([])
    for grid_row in grids:
        for x in range(grid_split):
            grid_row.append([])
            for i in range(5):
                grid_row[-1].append([])

    grid_index = -1
    pixel_row = -1
    grid_row_index = -1
    foo = []
    for index, pcolor in enumerate(pixel_data):

        if index % iter_grid == 0:
            grid_row_index  += 1

        if index % size[0] == 0:
            pixel_row += 1
            if pixel_row == grid_size[1]:
                pixel_row = 0

        if index % 5 == 0:
            grid_index += 1
            if grid_index == grid_split:
                grid_index = 0

        # we don't need the Alpha values
        pcolor = pcolor[:3] if len(pcolor) == 4 else pcolor
        x = grids[grid_row_index]
        y = x[grid_index]
        z = y[pixel_row]
        z.append(pcolor)

        foo.append("Index={} Color={} gri={} grid_index={} pixel_row={}".format(
            index, pcolor, grid_row_index, grid_index, pixel_row))

    grid_y_count = math.ceil(size[1] / grid_size[1])
    if grid_y_count != len(grids):
        error = "Expected {} grid row(s), found {}".format(
            grid_y_count, len(grids)
        )
        raise RuntimeError(error)

    grid_x_count = math.ceil(size[0] / grid_size[0])

    lines = [] 

    error = ["\n"]
    for row_index, grid_row in enumerate(grids):

        lines.append("[")

        if grid_x_count != len(grid_row):
            error.append("(Grid Row={}) Expected {} grid(s), found {}".format(
                row_index, grid_x_count, len(grid_row)
            ))
            #raise RuntimeError(error)

        for grid_index, grid in enumerate(grid_row):

            lines.append("  [")

            if len(grid) != grid_size[1]:
                error.append("(Grid Row={}, Grid Index={}) Expected {} "\
                    "grid row(s), found {}".format(
                    row_index, grid_index, grid_size[1], len(grid)
                ))
                #raise RuntimeError(error)
            for pr_index, pixel_row in enumerate(grid):
                if len(pixel_row) != grid_size[0]:
                    error.append("(Grid Row={}, Grid Index={}, Pixel Row={}) "\
                        "Expected {} grid row(s), found {}".format(
                        row_index, grid_index, pr_index, grid_size[1], len(pixel_row)
                    ))
                lines.append("    {}".format(pixel_row))
            lines.append("  ]")

        lines.append("]")

    with open('debug.txt', 'w') as x:
        x.write('\n'.join(lines))
    with open('out.txt', 'w') as x:
        x.write('\n'.join(foo))

    if len(error)>1:
        raise RuntimeError("\n".join(error))
    #raise Exception("asd")
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
    parser.add_argument('-c', '--csv',
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
        csv=args['csv']) 
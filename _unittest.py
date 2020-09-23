import shutil
import tempfile
import mosaic_mapper

TEST_IMG_COLORS = (
    (213, 223, 250), # light blue (background)
    (234, 27, 33), # red
    (97, 52, 0), # brown
    (255, 195, 13), # yellow
    (0, 0, 0), # black
    (0, 0, 254), # blue
)

TEST_IMG_MAPPING = (
    (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0, 2, 2, 2, 3, 3, 4, 3, 0, 0, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 2, 3, 2, 3, 3, 3, 4, 3, 3, 3, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 2, 3, 2, 2, 3, 3, 3, 4, 3, 3, 3, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0, 2, 3, 3, 3, 3, 4, 4, 4, 4, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0, 1, 1, 5, 1, 1, 5, 1, 1, 0, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 1, 1, 1, 5, 1, 1, 5, 1, 1, 1, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 1, 1, 1, 1, 5, 5, 5, 5, 1, 1, 1, 1, 0, 0, 0, 0),
    (0, 0, 0, 0, 3, 3, 1, 5, 3, 5, 5, 3, 5, 1, 3, 3, 0, 0, 0, 0),
    (0, 0, 0, 0, 3, 3, 3, 5, 5, 5, 5, 5, 5, 3, 3, 3, 0, 0, 0, 0),
    (0, 0, 0, 0, 3, 3, 5, 5, 5, 5, 5, 5, 5, 5, 3, 3, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0, 5, 5, 5, 0, 0, 5, 5, 5, 0, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 2, 2, 2, 0, 0, 0, 0, 2, 2, 2, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 2, 2, 2, 2, 0, 0, 0, 0, 2, 2, 2, 2, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
)


def unittest(image=None,
             destination=None,
             grid=(5, 5),
             validate_only=True):
    tmp_dir = destination or tempfile.mkdtemp()
    try:
        _unittest(image, grid, tmp_dir, validate_only)
    finally:
        if destination is None:
            shutil.rmtree(tmp_dir)


def _unittest(image, grid, tmp_dir, validate_only):
    image = image or _create_test_image(tmp_dir)

    # the library can do it's own internal validation
    # to assure the image hashes matches
    mosaic_mapper.run(image,
                      grid_size=grid,
                      destination=tmp_dir,
                      validate_only=validate_only)


def _create_test_image(tmp_dir):
    pixels = []
    for tim in TEST_IMG_MAPPING:
        pixels.append([])
        for index in tim:
            pixels[-1].append(TEST_IMG_COLORS[index])
    test_image = tempfile.mktemp(dir=tmp_dir, suffix='.png')
    mosaic_mapper.generate_image(test_image, pixels)
    return test_image


def _main():
    # this unit test was built to support passing through
    # external images for more extensive testing
    args = mosaic_mapper._args(image_nargs='?',
                               grid_size='5x5',
                               destination=None)
    unittest(args['image'],
             destination=args['destination'],
             grid=args['grid'],
             validate_only=not args['validate_only'])


if __name__ == '__main__':
    _main()
# mosaic_mapper

One time script for a client.

Takes an image and with a specific grid (5x5) it grids off the pixels, and builds a text file of each grid and the pixels with local 1:1 coordinates and the corresponding RGB values. The data can be validated by building a new image from the data and comparing hashes to ensure integrity.
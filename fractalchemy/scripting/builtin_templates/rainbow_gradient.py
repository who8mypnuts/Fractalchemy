# @name Rainbow gradient
# @category Colours
# @description Fills the palette with a full hue cycle.
import colorsys
saturation = param('Saturation', 0.8, min=0.0, max=1.0, step=0.05)
turns = param('Cycles', 1, min=1, max=6, help='How many times the rainbow repeats along the gradient')
gradient.colors = [tuple(int(255 * c) for c in colorsys.hsv_to_rgb((i * turns / 256) % 1.0, saturation, 1)) for i in range(256)]

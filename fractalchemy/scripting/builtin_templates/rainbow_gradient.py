# @name Rainbow gradient
# @category Colours
# @description Fills the palette with a full hue cycle.
import colorsys
saturation = input_number('Saturation (0-1)?', 0.8)
if saturation is None:
    stop()
gradient.colors = [tuple(int(255 * c) for c in colorsys.hsv_to_rgb(i / 256, saturation, 1)) for i in range(256)]

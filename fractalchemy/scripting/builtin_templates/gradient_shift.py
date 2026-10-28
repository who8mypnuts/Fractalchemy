# @name Warm / cool shift
# @category Colours
# @description Turns the hue of the whole gradient and boosts its saturation (the Gradient Library's sliders).
degrees = input_number('Hue shift (degrees, negative = cooler)?', 20)
if degrees is None:
    stop()
gradient.adjust(hue=degrees, saturation=10)

# @name Warm / cool shift
# @category Colours
# @description Turns the hue of the whole gradient and pushes its saturation (the Gradient Library's sliders), live.
degrees = param('Hue', 20, min=-180, max=180, help='Degrees: negative is cooler, positive warmer')
saturation = param('Saturation', 10, min=-100, max=100, help='Percent: -100 is grey, 100 vivid')
gradient.adjust(hue=degrees, saturation=saturation)

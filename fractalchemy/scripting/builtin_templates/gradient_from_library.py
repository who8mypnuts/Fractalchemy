# @name Gradient from a file
# @category Colours
# @description Loads a gradient from a file the Gradient Library reads (.ugr, .map, .flame, an image …).
path = input_text('Gradient file (.ugr, .map, .flame, .chaos, .fa or an image):', '')
if not path:
    stop()
index = input_number('Entry number in the file (0 = first):', 0)
gradient.load(path, int(index or 0))
print('loaded', path)

# @name Gradient from a file
# @category Colours
# @description Loads a gradient from a file the Gradient Library reads (.ugr, .map, .flame, an image …).
path = param('File', '', help='.ugr, .map, .flame, .chaos, .fa or an image')
index = param('Entry', 0, min=0, max=999, help='Which gradient of the file (0 = the first)')
if not path:
    print('Type a file name into the Parameters tab (File), then Run.')
    stop()
gradient.load(path, index)
print('loaded', path)

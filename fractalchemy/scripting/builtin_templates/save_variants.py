# @name Save rotated variants to a file
# @category Flame
# @description Appends several rotated copies of the flame to a .flame file of your choice (set the file in Parameters, then Run).
path = param('File', '', help='The .flame / .fa / .chaos file the variants are added to (a full path)')
count = param('Variants', 4, min=1, max=50)
spread = param('Rotation', 45, min=0, max=180, help='Each transform turns by a random angle up to this, either way')
if not path:
    print('Type a file name into the Parameters tab (File), then Run.')
    stop()
snapshot('original')
for i in range(count):
    restore('original')
    for t in transforms:
        t.rotate(random(-spread, spread))
    index = save_flame(path, f'{flame.name} variant {i + 1}')
    print('saved entry', index)
restore('original')

# @name Save rotated variants to a file
# @category Flame
# @description Appends several rotated copies of the flame to a .flame file of your choice.
path = input_text('Save the variants to which .flame / .fa file?', 'variants.flame')
if not path:
    stop()
count = int(input_number('How many variants?', 4) or 0)
snapshot('original')
for i in range(count):
    restore('original')
    for t in transforms:
        t.rotate(random(-45, 45))
    index = save_flame(path, f'{flame.name} variant {i + 1}')
    print('saved entry', index)
restore('original')

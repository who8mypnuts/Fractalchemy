# @name Scale all transforms
# @category Transforms
# @description Scales every transform about its origin by a factor you choose.
factor = input_number('Scale factor?', 0.9)
if factor is None:
    stop()
for t in transforms:
    t.scale(factor)

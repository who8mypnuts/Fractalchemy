# @name Scale all transforms
# @category Transforms
# @description Scales every transform about its origin by a factor you choose.
factor = param('Factor', 0.9, min=0.1, max=2.0, step=0.01)
for t in transforms:
    t.scale(factor)

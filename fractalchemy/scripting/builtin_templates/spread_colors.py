# @name Spread colours evenly
# @category Colours
# @description Distributes the transform colours evenly along the gradient.
n = len(transforms)
for i, t in enumerate(transforms):
    t.color = 0.5 if n == 1 else i / (n - 1)

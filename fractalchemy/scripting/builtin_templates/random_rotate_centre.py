# @name Random rotate about the centre
# @category Transforms
# @description Rotates every transform, position included, by a random angle about (0, 0).
for t in transforms:
    t.rotate_around(random(0, 360), 0, 0)

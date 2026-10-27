# @name Tile the plane
# @category Transforms
# @description A new flame: four half-scale linear transforms that tile the plane, plus one shaping transform.
new_flame('tiles')
for i, (x, y) in enumerate([(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5)]):
    t = add_transform(weight=0.5, color=i / 3, color_speed=0.2)
    t.set_affine(0.5, 0, 0, 0.5, x, y)
s = add_transform(weight=0.4, color=0.5, variations={'spherical': 1})
s.set_affine(0.6, 0, 0, 0.6, 0, 0)
gradient.random()
camera.fit()

# @name Spiral
# @category Transforms
# @description A new flame: a logarithmic spiral from a scaled-and-rotated transform plus a decorative one.
turn = param('Rotation per step', 25, min=-90, max=90)
shrink = param('Shrink per step', 0.92, min=0.5, max=0.99, step=0.01)
new_flame('spiral')
a = add_transform(weight=0.85, color=0, color_speed=0.3)
a.set_affine(shrink, 0, 0, shrink, 0.12, 0).rotate(turn)
b = add_transform(weight=0.15, color=1, color_speed=0.8, variations={'spherical': 0.6, 'linear': 0.4})
b.set_affine(0.35, 0, 0, 0.35, 0.9, 0.3)
gradient.random()
camera.fit()

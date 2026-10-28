# @name Spiral
# @category Transforms
# @description A new flame: a logarithmic spiral from a scaled-and-rotated transform plus a decorative one.
new_flame('spiral')
turn = input_number('Rotation per step (degrees)?', 25)
if turn is None:
    stop()
a = add_transform(weight=0.85, color=0, color_speed=0.3)
a.set_affine(0.92, 0, 0, 0.92, 0.12, 0).rotate(turn)
b = add_transform(weight=0.15, color=1, color_speed=0.8, variations={'spherical': 0.6, 'linear': 0.4})
b.set_affine(0.35, 0, 0, 0.35, 0.9, 0.3)
gradient.random()
camera.fit()

# @name Julia mutation
# @category Transforms
# @description The classic Apophysis "Julia" script: pushes the transforms outwards and adds a julian transform.
power = param('Power', 0, min=0, max=12, help='julian_power; 0 picks one at random (2 to 6)')
distance = param('Distance', 0.0, min=-3.0, max=3.0, step=0.25, help='julian_dist; 0 picks one at random')
spread = param('Spread', 0.4, min=0.0, max=1.0, step=0.05, help='How far the existing transforms are pushed')
for t in transforms:
    t.translate(random(-spread, spread), random(-spread, spread))
j = add_transform(weight=total_weight(), color=random(), variations={'julian': 1})
j.params['julian_power'] = power or random_int(2, 6)
j.params['julian_dist'] = distance or random_choice([1, 1, -1, 2])
j.set_affine(0.8, 0, 0, 0.8, 0, 0)
camera.fit()
print('julian power', j.params['julian_power'], 'dist', j.params['julian_dist'])

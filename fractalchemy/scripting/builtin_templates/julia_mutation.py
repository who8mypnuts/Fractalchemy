# @name Julia mutation
# @category Transforms
# @description The classic Apophysis "Julia" script: pushes the transforms outwards and adds a julian transform.
for t in transforms:
    t.translate(random(-0.4, 0.4), random(-0.4, 0.4))
j = add_transform(weight=total_weight(), color=random(), variations={'julian': 1})
j.params['julian_power'] = random_int(2, 6)
j.params['julian_dist'] = random_choice([1, 1, -1, 2])
j.set_affine(0.8, 0, 0, 0.8, 0, 0)
camera.fit()
print('julian power', j.params['julian_power'], 'dist', j.params['julian_dist'])

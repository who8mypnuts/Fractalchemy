# @name Gnarl
# @category Transforms
# @description A new flame: a near-identity transform with small popcorn2 / waves2 warps — the classic gnarl.
new_flame('gnarl')
g = add_transform(weight=1, color=0.2, color_speed=0.05, variations={'linear': 1, 'popcorn2': 0.12, 'waves2': 0.08})
g.params.update(popcorn2_x=random(0.05, 0.3), popcorn2_y=random(0.05, 0.3), popcorn2_c=random(2, 5),
                waves2_freqx=random(2, 5), waves2_freqy=random(2, 5), waves2_scalex=0.12, waves2_scaley=0.12)
g.set_affine(0.98, 0, 0, 0.98, 0, 0).rotate(random(-6, 6))
l = add_transform(weight=0.05, color=0.9, color_speed=0.5)
l.set_affine(0.5, 0, 0, 0.5, 0.4, 0.2)
gradient.random()
camera.fit()

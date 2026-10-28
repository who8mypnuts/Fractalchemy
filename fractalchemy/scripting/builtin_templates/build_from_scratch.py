# @name Build a flame from scratch
# @category Flame
# @description A commented walk-through of the whole API: transforms, variations, colours, xaos and the camera.
new_flame('scripted flame')

# 1. transforms
a = add_transform(weight=1, color=0, color_speed=0.4)
a.set_affine(0.6, 0, 0, 0.6, -0.4, 0)           # a b c d e f: shrink and move left
a.set_variation('linear', 0.5).set_variation('spherical', 0.5)

b = add_transform(weight=0.7, color=0.6, color_speed=0.6)
b.set_affine(0.7, 0, 0, 0.7, 0.5, 0.2).rotate(60)
b.variations['linear'] = 0                       # remove linear
b.variations['julian'] = 1                       # add julian with default parameters
b.params['julian_power'] = 4

c = add_transform(weight=0.3, color=1, color_speed=0.9, variations={'bubble': 1})
c.set_affine(0.4, 0, 0, 0.4, 0, -0.5)

# 2. xaos: c is only reachable from a
xaos.set(b, c, 0)

# 3. colours
gradient.set_stops([(0, '#05070f'), (0.4, '#0f7d4a'), (0.7, '#b96bff'), (1, '#f2e6ff')])
coloring.brightness = 5
coloring.gamma = 3.5

# 4. camera
camera.fit()
print('done:', len(transforms), 'transforms')

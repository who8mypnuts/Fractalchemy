# @name Random rotate all transforms
# @category Transforms
# @description Rotates every transform by a random angle about its own origin (the Parameters tab sets the range live).
max_angle = param('Maximum rotation', 360, min=0, max=360, help='Each transform turns by a random angle up to this, either way')
for t in transforms:
    angle = random(-1, 1) * max_angle
    t.rotate(angle)
    print(f'transform {t.index + 1} rotated by {angle:.1f}°')

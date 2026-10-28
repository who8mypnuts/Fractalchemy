# @name Random rotate all transforms
# @category Transforms
# @description Rotates every transform by a random angle about its own origin.
max_angle = input_number('Maximum rotation (degrees)?', 360)
if max_angle is None:
    stop()
for t in transforms:
    angle = random(-max_angle, max_angle)
    t.rotate(angle)
    print(f'transform {t.index + 1} rotated by {angle:.1f}°')

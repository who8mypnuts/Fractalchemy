# @name Live kaleidoscope
# @category Transforms
# @description Folds the fractal into a kaleidoscope: symmetry order, twist and zoom on live controls.
order = param('Order', 6, min=2, max=16, help='How many-fold the pattern repeats')
mirror = param('Mirror', True, help='Mirror as well as rotate (dihedral symmetry)')
twist = param('Twist', 0.0, min=-45.0, max=45.0, step=0.5, help='Turns every existing transform a little')
scale = param('Scale', 1.0, min=0.5, max=1.5, step=0.01, help='Scales every existing transform about its origin')
for t in transforms:
    t.rotate(twist)
    t.scale(scale)
add_symmetry(-order if mirror else order)
xaos.reset()
camera.fit()
print(f'{order}-fold kaleidoscope', '(mirrored)' if mirror else '')

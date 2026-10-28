# @name Fit camera to the fractal
# @category Camera
# @description Frames the attractor the way the Random Batch does.
if camera.fit():
    print('camera:', camera)
else:
    print('could not frame the fractal (it blows up or collapses)')

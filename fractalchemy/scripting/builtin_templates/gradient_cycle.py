# @name Gradient cycle preview
# @category Colours
# @description Animates the gradient rotating through the fractal in the main window (uses update()).
for i in range(16):
    gradient.rotate(16)
    progress(i / 16)
    update()
    sleep(0.1)

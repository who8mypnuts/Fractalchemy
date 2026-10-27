# @name Camera spin preview
# @category Camera
# @description Rotates the camera in steps, re-rendering each — a mini animation preview.
steps = 12
for i in range(steps):
    camera.rotate_by(360 / steps)
    progress((i + 1) / steps)
    update()
    sleep(0.15)

# @name 3D tilt
# @category Camera
# @description Tilts the plane with the 3D camera and adds a little perspective.
camera.pitch = param('Pitch', 35, min=-90, max=90)
camera.yaw = param('Yaw', 15, min=-180, max=180)
camera.perspective = param('Perspective', 0.15, min=0.0, max=1.0, step=0.01)

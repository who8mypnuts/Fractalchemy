# @name 3D tilt
# @category Camera
# @description Tilts the plane with the 3D camera and adds a little perspective.
camera.pitch = input_number('Pitch (degrees)?', 35) or 0
camera.yaw = input_number('Yaw (degrees)?', 15) or 0
camera.perspective = 0.15

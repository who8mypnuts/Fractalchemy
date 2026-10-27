# @name Mirror horizontally
# @category Transforms
# @description Flips every transform (and the final transform) in the vertical axis.
for t in transforms:
    t.flip_horizontal()
if final_transform() is not None:
    final_transform().flip_horizontal()
camera.x = -camera.x

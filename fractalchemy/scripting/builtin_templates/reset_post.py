# @name Reset post transforms
# @category Transforms
# @description Sets every post transform back to the identity.
for t in transforms:
    t.reset_post()
if final_transform() is not None:
    final_transform().reset_post()

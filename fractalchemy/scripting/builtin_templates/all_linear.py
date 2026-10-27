# @name Reset variations to linear
# @category Transforms
# @description Replaces every variation with linear = 1, keeping affines, colours and weights.
for t in transforms:
    t.clear_variations()
    t.set_variation('linear', 1)
    t.params = {}

# @name Add random transform
# @category Transforms
# @description Appends a transform with a random affine and random variations (Apophysis: Add random transform).
t = add_random_transform()
print('added transform', t.index + 1, 'with', ' + '.join(t.variation_names))

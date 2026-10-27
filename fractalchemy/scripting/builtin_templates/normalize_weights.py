# @name Normalize weights
# @category Transforms
# @description Scales the transform weights so they add up to 1 (Apophysis: Normalize Weights).
normalize_weights()
for t in transforms:
    print(f'transform {t.index + 1}: weight {t.weight:.4f}')

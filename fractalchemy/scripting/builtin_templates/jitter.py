# @name Mutate (jitter) coefficients
# @category Transforms
# @description Nudges every affine coefficient a little — a quick way to explore nearby fractals (New seed rolls again).
amount = param('Amount', 0.05, min=0.0, max=0.5, step=0.01)
for t in transforms:
    t.coefs = [c + random_gauss(0, 1) * amount for c in t.coefs]

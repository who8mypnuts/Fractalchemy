# @name Mutate (jitter) coefficients
# @category Transforms
# @description Nudges every affine coefficient a little — a quick way to explore nearby fractals.
amount = input_number('Jitter amount (0.01 - 0.5)?', 0.05)
if amount is None:
    stop()
for t in transforms:
    t.coefs = [c + random_gauss(0, amount) for c in t.coefs]

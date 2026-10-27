# @name Make rotational symmetry
# @category Transforms
# @description Adds rotated linear copies so the whole fractal gets N-fold rotational symmetry (the classic Apophysis trick).
n = input_number('Symmetry order (2-12)?', 3)
if n is None or n < 2:
    stop('cancelled')
n = int(n)
weight = total_weight()
for i in range(1, n):
    t = add_transform(weight=weight, color_speed=0, color=0, name=f'symmetry {i}')
    t.rotate(360 * i / n)
xaos.reset()
print(f'{n}-fold symmetry: {n - 1} transforms added')

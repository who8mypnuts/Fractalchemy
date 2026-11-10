# @name Make rotational symmetry
# @category Transforms
# @description Adds rotated linear copies so the whole fractal gets N-fold rotational symmetry (the classic Apophysis trick).
n = param('Order', 3, min=2, max=12, help='How many-fold the symmetry is')
mirror = param('Mirror too', False, help='Dihedral symmetry: a left-right mirror as well as the rotations')
added = add_symmetry(-n if mirror else n)
xaos.reset()
print(f'{n}-fold symmetry{" with a mirror" if mirror else ""}: {added} transforms added')

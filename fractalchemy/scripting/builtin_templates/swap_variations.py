# @name Random variation swap
# @category Transforms
# @description Keeps linear and replaces every other variation with a random one of the same weight.
for t in transforms:
    for name in t.variation_names:
        if name == 'linear':
            continue
        weight = t.get_variation(name)
        t.remove_variation(name)
        new = random_variation(exclude=['pre_blur', 'blur', 'noise', name])
        t.set_variation(new, weight)
        print(f'transform {t.index + 1}: {name} -> {new}')

# @name Flame report
# @category Flame
# @description Prints everything about the current flame to the output panel.
clear()
print('Flame:', flame.name, f'{camera.width}x{camera.height}')
print(coloring)
print(camera)
for t in transforms:
    print(f'--- transform {t.index + 1}', f'({t.name})' if t.name else '')
    print('  coefs', [round(c, 4) for c in t.coefs])
    print(f'  weight {t.weight:.4f}  color {t.color:.3f}  speed {t.color_speed:.3f}  opacity {t.opacity}')
    print('  variations', t.variations)
    if t.params:
        print('  params', t.params)
if final_transform() is not None:
    print('final transform:', final_transform().variations)
print('xaos:' if not xaos.is_default else 'xaos: none')
if not xaos.is_default:
    print(xaos)

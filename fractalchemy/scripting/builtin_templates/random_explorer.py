# @name Random flame explorer
# @category Flame
# @description Shows random flames one after another; answer Yes to keep the current one.
names = [n for n in ['linear', 'spherical', 'swirl', 'julian', 'bubble', 'polar', 'pdj', 'curl', 'disc'] if n in list_variations()]
for i in range(20):
    random_flame(names, transforms=(2, 4))
    update()
    if confirm(f'Keep this flame? ({i + 1} of 20; No = try another)'):
        break

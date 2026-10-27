# @name Random xaos
# @category Xaos
# @description Random on / off links with a chosen density; every transform keeps at least one way out.
p = input_number('Link probability (0-1)?', 0.6)
if p is None:
    stop()
xaos.randomize(p)
print(xaos)

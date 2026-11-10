# @name Random xaos
# @category Xaos
# @description Random on / off links with a chosen density; every transform keeps at least one way out.
p = param('Link probability', 0.6, min=0.0, max=1.0, step=0.05)
xaos.randomize(p)
print(xaos)

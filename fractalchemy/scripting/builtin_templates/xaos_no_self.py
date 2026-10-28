# @name Xaos: no self loops
# @category Xaos
# @description Transforms never follow themselves.
xaos.from_function(lambda i, j: 0 if i == j else 1)
print(xaos)

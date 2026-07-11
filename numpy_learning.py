import numpy as np

A = np.array([1, 1, 1])[:, np.newaxis]
B = np.array([2, 2, 2])[:, np.newaxis]

C = np.vstack((A, B))
D = np.hstack((A, B))# horizontal 

E = np.concatenate((A, B, A, A), axis = 1)

F = np.arange(12).reshape(3, 4)


print(np.vsplit(F, 3))
print(np.hsplit(F, 2))
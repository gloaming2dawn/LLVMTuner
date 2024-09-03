import numpy as np

def find_allzero_columns(matrix):
    return np.where(np.all(matrix == 0, axis=0))[0]
def find_anynonzero_rows(matrix, inds):
    return matrix[:, inds].sum(axis=1)!=0

def find_allpositive_columns(matrix):
    return np.where(np.all(matrix > 0, axis=0))[0]
def find_anyzero_rows(matrix, inds):
    X = matrix[:, inds]
    return np.any(X == 0, axis=1)

def find_far_cands(X, cand_X):
    # if some candidates in cand_X are far from (distance in a given feature dimension > 0.5) all samples of X in some feature dimensions, return both these features indices and the corresponding candidates indices/mask
    return 


# 手动创建一个 5x5 的矩阵
X = np.array([[1, 0, 3, 0, 5],
              [6, 0, 8, 0, 7],
              [1, 0, 3, 0, 5],
              [1, 0, 3, 0, 5],
              [1, 0, 3, 0, 5]])

cand_X = np.array([[1, 1, 3, 0, 5],
                   [1, 0, 3, 2, 5],
                   [1, 0, 3, 0, 5]])
inds = find_allzero_columns(X)
print(inds)
mask = find_anynonzero_rows(np.array(cand_X), inds)
print(mask)



# 手动创建一个 5x5 的矩阵
X = np.array([[1, 1, 3, 1, 5],
              [6, 1, 8, 1, 7],
              [1, 1, 3, 1, 5],
              [1, 1, 3, 1, 5],
              [1, 1, 3, 0, 5]])

cand_X = np.array([[0, 1, 3, 1, 5],
                   [1, 0, 3, 2, 5],
                   [1, 1, 3, 0, 5]])
inds = find_allpositive_columns(X)
print(inds)
mask = find_anyzero_rows(np.array(cand_X), inds)
print(mask)


# 手动创建一个 5x5 的矩阵
X = np.array([[1.0, 1, 0.3, 1, 0.5],
              [0.9, 1, 0.8, 1, 0.7],
              [1.0, 1, 0.3, 1, 0.5],
              [1.0, 1, 0.3, 1, 0.5],
              [1.0, 1, 0.3, 0, 0.5]])

cand_X = np.array([[0.1, 0.1, 0.3, 0.1, 0.5],
                   [0.5, 0.3, 0.3, 0.2, 0.5],
                   [0.5, 0.6, 0.3, 0.0, 0.5]])
# inds = find_allpositive_columns(X)
# print(inds)
# mask = find_anyzero_rows(np.array(cand_X), inds)
# print(mask)
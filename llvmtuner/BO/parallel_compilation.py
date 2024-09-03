from multiprocessing import Pool

def square(x):
    return x * x

if __name__ == "__main__":
    with Pool() as p:
        p.map(square, range(1000))

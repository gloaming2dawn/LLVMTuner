import random as random
from multiprocessing import Pool
from copy import deepcopy
import time
from math import inf

import llvmtuner
from llvmtuner.searchspace import default_space, passlist2str, parse_O3string


class random_optimizer:
    def __init__(self, fun, passes, budget, len_seq=100):
        self.fun = fun
        self.passes = passes
        self.len_seq = len_seq
        self.budget = budget
        if fun.hotfiles is None:
            module2funcnames = fun._get_func_names()
            self.hotfiles = list(module2funcnames.keys())
        else:
            self.hotfiles = fun.hotfiles

    def random_params(self, i):
        params={}
        for fileroot in self.hotfiles:
            seq=random.choices(self.passes, k=self.len_seq)
            params[fileroot]=passlist2str(deepcopy(seq))
        return params

    def minimize(self):
        params_list = []
        with Pool() as p:
            params_list = list(p.map(self.random_params, range(self.budget)))
        t0 = time.time()
        with Pool() as p:
            flags = p.map(self.fun.gen_optIR, params_list)
            # flags = p.map(self.fun.build, params_list) # this is wrong, because parallel build will cause conflict (binary file is the same)
        print(f'time of parallel generating {self.budget} optimized IRs:',time.time()-t0)
        print(f"Number of successful compilation: {sum(flags)}")

        
        for i in range(len(params_list)):
            if flags[i]:
                y = self.fun(params_list[i])

        return self.fun.best_params, self.fun.best_y
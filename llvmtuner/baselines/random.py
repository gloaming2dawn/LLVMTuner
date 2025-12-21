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
        self.n = min(50, int(self.budget/len(self.hotfiles)/3)+1) # max number of consecutive failures
        self.best_params = {k:'default<O3>' for k in self.hotfiles}
        self.best_y = float('inf')

    # def random_params(self, file):
    #     params={}
    #     for fileroot in self.hotfiles:
    #         seq=random.choices(self.passes, k=self.len_seq)
    #         params[fileroot]=passlist2str(deepcopy(seq))
    #     return params

    def search(self, file):
        params = deepcopy(self.best_params)
        seq=random.choices(self.passes, k=self.len_seq)
        params[file]=passlist2str(deepcopy(seq))
        y = self.fun(params)
        return params, y

    def minimize(self):
        n_iterations = 0
        while (n_iterations< self.budget):
            for file in self.hotfiles:
                print(f'search file {file}')
                failure_count = 0 
                while failure_count < self.n:
                    params, result = self.search(file)
                    n_iterations += 1
                    if result < self.best_y:
                        self.best_y = result
                        self.best_params = deepcopy(params)
                        failure_count = 0  # 重置连续失败次数
                    else:
                        failure_count += 1 
                    if n_iterations >= self.budget:
                        return self.best_params, self.best_y

        return self.best_params, self.best_y
    
        # for i in range(self.budget):
        #     params = self.random_params(i)
        #     y = self.fun(params)
        
    
        # params={}
        # for fileroot in self.hotfiles:
        #     params[fileroot]='default<O3>'
        #     y = self.fun(params)


        # params_list = []
        # with Pool() as p:
        #     params_list = list(p.map(self.random_params, range(self.budget)))
        # t0 = time.time()
        # with Pool() as p:
        #     flags = p.map(self.fun.gen_optIR, params_list)
        #     # flags = p.map(self.fun.build, params_list) # this is wrong, because parallel build will cause conflict (binary file is the same)
        # print(f'time of parallel generating {self.budget} optimized IRs:',time.time()-t0)
        # print(f"Number of successful compilation: {sum(flags)}")

        
        # for i in range(len(params_list)):
        #     if flags[i]:
        #         y = self.fun(params_list[i])

        
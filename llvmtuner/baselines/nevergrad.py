
import llvmtuner
from llvmtuner.searchspace import default_space, passlist2str, parse_O3string

import nevergrad as ng
import numpy as np
import time
from math import e, inf
from copy import deepcopy

class nevergrad_optimizer:
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

    def search(self, file):
        params = deepcopy(self.best_params)
        t0=time.time()
        x = self.optimizers[file].ask()
        # print(f'ask time:',time.time()-t0)
        pass_list=list(x.value)
        params[file] = passlist2str(pass_list) 
        y=self.fun(params)
        if y != inf:
            t0=time.time()
            self.optimizers[file].tell(x, y)
            # print(f'tell time:',time.time()-t0)
        return params, y
    
    def minimize(self):
        self.optimizers = {}
        for file in self.hotfiles:
            params_set = ng.p.Choice(
                    choices=self.passes,
                    repetitions=self.len_seq,
                    deterministic=True
                )
            self.optimizers[file]=ng.optimizers.NGOpt(parametrization=params_set, budget=self.budget)  

        n_iterations = 0
        while (n_iterations< self.budget):
            for file in self.hotfiles:
                print(f'search file {file}')
                failure_count = 0 
                while failure_count < self.n:
                    params, result = self.search(file)
                    n_iterations += 1
                    print(n_iterations)
                    if result < self.best_y:
                        self.best_y = result
                        self.best_params = deepcopy(params)
                        failure_count = 0  # 重置连续失败次数
                    else:
                        failure_count += 1 
                    if n_iterations >= self.budget:
                        return self.best_params, self.best_y
                    

        return self.best_params, self.best_y
    
    # def minimize(self):
    #     params_set = ng.p.Choice(
    #             choices=self.passes,
    #             repetitions=self.len_seq,
    #             deterministic=True
    #         )

    #     optimizer=ng.optimizers.NGOpt(parametrization=params_set, budget=self.budget)

    #     count = 0
    #     while count < self.budget:
    #         t0=time.time()
    #         x = optimizer.ask()
    #         print(f'ask time:',time.time()-t0)
    #         pass_list=list(x.value)
    #         params = passlist2str(pass_list)            
    #         y=self.fun(params)
    #         if y != inf:
    #             t0=time.time()
    #             optimizer.tell(x, y)
    #             print(f'tell time:',time.time()-t0)
    #             count += 1

    #     return self.fun.best_params, self.fun.best_y
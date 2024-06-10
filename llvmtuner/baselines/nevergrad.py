
import llvmtuner
from llvmtuner.searchspace import default_space, passlist2str, parse_O3string

import nevergrad as ng
import numpy as np
import time
from math import inf
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

    def minimize(self):
        params_set = ng.p.Choice(
                choices=self.passes,
                repetitions=self.len_seq,
                deterministic=True
            )

        optimizer=ng.optimizers.NGOpt(parametrization=params_set, budget=self.budget)

        count = 0
        while count < self.budget:
            t0=time.time()
            x = optimizer.ask()
            print(f'ask time:',time.time()-t0)
            pass_list=list(x.value)
            params = passlist2str(pass_list)            
            y=self.fun(params)
            if y != inf:
                t0=time.time()
                optimizer.tell(x, y)
                print(f'tell time:',time.time()-t0)
                count += 1

        return self.fun.best_params, self.fun.best_y
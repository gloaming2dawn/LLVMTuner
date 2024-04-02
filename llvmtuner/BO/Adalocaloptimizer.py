###############################################################################
# Copyright (c) 2019 Uber Technologies, Inc.                                  #
#                                                                             #
# Licensed under the Uber Non-Commercial License (the "License");             #
# you may not use this file except in compliance with the License.            #
# You may obtain a copy of the License at the root directory of this project. #
#                                                                             #
# See the License for the specific language governing permissions and         #
# limitations under the License.                                              #
###############################################################################
from math import inf
import hashlib
import math
import json
import os
from time import time
import sys
from copy import deepcopy
import subprocess
import random
# from pathos.multiprocessing import Pool
from multiprocessing import Pool
import itertools

import gpytorch
from gpytorch.mlls import ExactMarginalLogLikelihood

import numpy as np
import torch
from torch.quasirandom import SobolEngine
from sklearn.preprocessing import power_transform, PowerTransformer

from .gp import train_gp
#from utils import from_unit_cube, latin_hypercube, to_unit_cube

import cma

import botorch
from botorch.acquisition import qNoisyExpectedImprovement, qExpectedImprovement, ExpectedImprovement, UpperConfidenceBound, qUpperConfidenceBound, qLowerBoundMaxValueEntropy, AnalyticAcquisitionFunction
from botorch.optim import optimize_acqf
from botorch.fit import fit_gpytorch_model
from botorch.utils.sampling import draw_sobol_samples
from botorch.utils.transforms import unnormalize

import warnings
warnings.simplefilter("ignore", cma.evolution_strategy.InjectionWarning)
import gc

import nevergrad as ng
import llvmtuner
from llvmtuner.searchspace import default_space, passlist2str

def read_seq_json_from_subdirs(base_dir):
    seq_strings = []  # 存储从seq.json文件中读取的字符串
    # 遍历给定目录
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        # 检查当前路径是否为文件夹
        if os.path.isdir(item_path):
            seq_file_path = os.path.join(item_path, 'seq.json')
            # 尝试读取seq.json文件
            try:
                with open(seq_file_path, 'r', encoding='utf-8') as f:
                    # 假设文件内容直接是一个字符串
                    content = json.load(f)
                    seq_strings.append(content)
            except FileNotFoundError:
                # seq.json文件不存在于当前子文件夹中
                raise ValueError(f"Not found: {seq_file_path}")
            except json.JSONDecodeError:
                # seq.json文件内容不是有效的JSON，可能需要错误处理
                raise ValueError(f"Error decoding JSON from file: {seq_file_path}")
    
    return seq_strings

def permu_best(best_params, fileroot, opt_str):
    cand_params = deepcopy(best_params)
    cand_params[fileroot] = opt_str
    return cand_params

def permu_best_k(best_params, k, cands):
    cand_params = deepcopy(best_params)
    fileroots = random.sample(list(cand_params.keys()), k=k)
    print(k, fileroots)
    for fileroot in fileroots:
        seqs = cands[fileroot]
        opt_str = random.choice(seqs)
        cand_params[fileroot] = opt_str
    return cand_params


def nonzero_rows(matrix, inds):
    return matrix[:, inds].sum(axis=1)!=0

class params2vec:
    def __init__(self, seq2vec):
        self.seq2vec = seq2vec
    def __call__(self, params):
        x = []
        for fileroot, seq in params.items():
            vec = self.seq2vec[fileroot][seq]
            x.append(vec)
        x = np.concatenate(x)
        return x





class Adalocaloptimizer:

    def __init__(
        self,
        fun,
        len_seq,
        budget, 
        passes,
        precompiled_path=None, # path that contains a large number of precompiled IR and their optimization configs
        n_parallel=50,
        n_init=20,
        max_cand_seqs = 1000,
        batch_size=1,
        failtol=50,
        verbose=True,
        seed = None,
        initial_guess=None,
    ):

        # Basic input checks
        assert budget > 0 and isinstance(budget, int)
        assert batch_size > 0 and isinstance(batch_size, int)
        assert n_init > 0 and isinstance(n_init, int)
        assert isinstance(verbose, bool)
        assert budget > n_init and budget > batch_size

        self.fun=fun
        self.gen_ir_fun=fun.gen_optIR
        self.build_fun = fun.build
        self.eval_fun = fun.measure
        self.tmp_dir=fun.tmp_dir
        self.passes=passes
 
        
        self.len_seq=len_seq
        self.n_init = n_init
        self.n_evals = 0
        self.budget = budget
        self.batch_size = batch_size
        self.verbose = verbose


        self.n_parallel = n_parallel
        self.max_cand_seqs=max_cand_seqs
        
        
        

        # Save the full history
        self.params_list, self.fX = [], []
        self.best_y = inf
        
        self.cands= {}
        for filename in self.fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            self.cands[fileroot]=[]
        
        self.precompiled_path = precompiled_path
        if precompiled_path is not None:
            assert precompiled_path == self.tmp_dir, "precompiled IRs should be put into tmp_dir"
            for filename in self.fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                self.cands[fileroot]=read_seq_json_from_subdirs(os.path.join(precompiled_path, fileroot))
                
            
        
        
        self.new_seqs= []
        self.seq_next, self.fX_next = '', inf
        
        
        
        self.failcount = 0
        self.succcount = 0
        self.failtol = failtol
        self.k = len(self.fun.hotfiles)

        self.initialization = True

        
        self.initial_guess=initial_guess
        
        if seed is not None:
            self.seed = seed
        else:
            self.seed = np.random.randint(1e5)
    
    
    
    def update_k(self, fX_next):
        if np.min(fX_next) < self.best_y - 1e-3 * math.fabs(self.best_y):
            self.failcount = 0
            self.succcount +=1
        else:
            self.failcount += self.batch_size
            self.succcount = 0
            
        # if self.succcount == 3:
        #     self.length = min([2.0 * self.length, 0.5])
        #     self.succcount = 0

        if self.failcount > self.failtol:
            self.k = max([int(self.k/2), 1]) 
            self.failcount = 0 
            
    
    
        
    def ask(self):
        
        if len(list(self.cands.values())[0]) > self.max_cand_seqs:
            return None
        
        new_cands= {}
        for filename in self.fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            new_cands[fileroot]=[]
            for _ in range(200):
                seq=random.choices(self.passes, k=self.len_seq)
                opt_str = passlist2str(seq)
                if opt_str not in self.cands[fileroot]:
                    new_cands[fileroot].append(opt_str)
        

        return new_cands
    
    
        
        
        
    def genIR_and_update(self, new_cands):   
        t0 = time()   
        params_list=[]
        num=len(list(new_cands.values())[0])
        for i in range( num ):
            params = {}
            for fileroot in new_cands:
                params[fileroot]=new_cands[fileroot][i]
            params_list.append(params)
            
        
        with Pool() as p:
            p.map(self.gen_ir_fun, params_list)
            
        if self.verbose:
            print("Opt {} candidates cost {:.4f}".format(len(params_list), time()-t0))        
        

    
    
    
    
    
    def tell(self, params_next, fX_next):
        self.update_k(fX_next)
        self.n_evals += 1
        self.fX.append(fX_next)
        self.params_list.append(params_next)
        self.best_params = self.params_list[np.argmin(self.fX)]
        self.best_y=np.min(self.fX)
        



    def minimize(self):
        """Run the full optimization process."""
        
        epochs=0
        self.failcount = 0
        
        # firstly build the program in '-O3'
        assert self.build_fun('default<O3>')
        
        # Initialization
        initial_params_list = []
        ii=0
        if self.initial_guess is None:
            ii=0
        else:
            ii=1
            initial_params={}
            if isinstance(self.initial_guess, (str)):
                for filename in self.fun.hotfiles:
                    fileroot,fileext=os.path.splitext(filename)
                    initial_params[fileroot]=self.initial_guess
            else:
                initial_params = self.initial_guess
            initial_params_list.append(initial_params)
            self.initial_guess=None
        
        for _ in range(self.n_init - ii):
            if self.precompiled_path is None:
                seq=random.choices(self.passes, k=self.len_seq)
                opt_str = passlist2str(seq)
                params={}
                for filename in self.fun.hotfiles:
                    fileroot,fileext=os.path.splitext(filename)
                    params[fileroot]=opt_str
                    if opt_str not in self.cands[fileroot]:
                        self.cands[fileroot].append(opt_str)
                if params not in initial_params_list:
                    initial_params_list.append(params)
            else:
                params={}
                for filename in self.fun.hotfiles:
                    fileroot,fileext=os.path.splitext(filename)
                    params[fileroot]=random.choice(self.cands[fileroot])
                initial_params_list.append(params)
            
        
        
        print('len_init_samples:',len(initial_params_list))
        
        for params in initial_params_list:
            fX_next = self.fun(params)
            if fX_next != inf:
                self.tell(params, fX_next)
                
            
                

            
        
        


        
        # print('cost time:', time()-t0)
        if self.precompiled_path is None:
            new_cands = self.ask()
            if new_cands is not None:
                self.genIR_and_update(new_cands)
                new_cands, _, _ = self.cands2vecs(new_cands)
                for fileroot in self.cands:
                    self.cands[fileroot].extend(new_cands[fileroot])
                    

        while self.n_evals < self.budget:
            if self.precompiled_path is None:
                # ask new candidates
                new_cands = self.ask()
                
                if new_cands is not None:
                    # generate optimized IRs parallely and update
                    self.genIR_and_update(new_cands)
                    new_cands, _, _ = self.cands2vecs(new_cands)
                    for fileroot in self.cands:
                        self.cands[fileroot].extend(new_cands[fileroot])


            params_next = permu_best_k(self.best_params, self.k, self.cands)
            if params_next in self.params_list:
                for _ in range(50):
                    params_next = permu_best_k(self.best_params, self.k, self.cands)
                    if params_next not in self.params_list:
                        break
            fX_next = self.fun(params_next)
            
                    
            # update
            self.tell(params_next, fX_next)
            
            
if __name__ == "__main__":
    pass

                



                


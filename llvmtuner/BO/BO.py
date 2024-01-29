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
# from pymoo.algorithms.soo.nonconvex.ga import GA
# from pymoo.core.problem import Problem
# from pymoo.core.evaluator import Evaluator
# from pymoo.core.termination import NoTermination
import llvmtuner
from llvmtuner import searchspace
from llvmtuner import globalvar
from llvmtuner.feature_extraction import read_optstats_from_cfgjsonlist, stats2vec


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

def permu_best(best_params, fileroot, opt_str):
    cand_params = deepcopy(best_params)
    cand_params[fileroot] = opt_str
    return cand_params


def check_seq(seq):
    cgprofile_count = seq.count('-cg-profile')
    if cgprofile_count>1:
        for _ in range(cgprofile_count-1):
            index = seq.index('-cg-profile')
            seq[index] = ''
    return seq


def nonzero_rows(matrix, inds):
    return matrix[:, inds].sum(axis=1)!=0



class BO:
    """Multi-level acquisition function optimization based Bayesian Optimization

    Parameters
    ----------
    f : function handle
    lb : Lower variable bounds, numpy.array, shape (d,).
    ub : Upper variable bounds, numpy.array, shape (d,).
    n_init : Number of initial points (2*dim is recommended), int.
    max_evals : Total evaluation budget, int.
    batch_size : Number of points in each batch, int.
    verbose : If you want to print information about the optimization progress, bool.
    use_ard : If you want to use ARD for the GP kernel.
    max_cholesky_size : Largest number of training points where we use Cholesky, int
    n_training_steps : Number of training steps for learning the GP hypers, int
    min_cuda : We use float64 on the CPU if we have this or fewer datapoints
    device : Device to use for GP fitting ("cpu" or "cuda")
    dtype : Dtype to use for GP fitting ("float32" or "float64")

    Example usage:
        turbo1 = Turbo1(f=f, lb=lb, ub=ub, n_init=n_init, max_evals=max_evals)
        turbo1.optimize()  # Run optimization
        X, fX = turbo1.X, turbo1.fX  # Evaluated points
    """

    def __init__(
        self,
        fun,
        len_seq,
        budget, 
        passes=llvmtuner.searchspace.default_space(),
        n_parallel=50,
        n_init=20,
        max_cand_seqs = 1000,
        batch_size=1,
        acqf='UCB', # 'EI' or 'UCB'
        beta=1.96, # only useful when acq=UCB, used to trade off exploration and exploitation
        # n_init_acq=512,
        # max_acq_size=128,
        # n_restarts_acq=1,
        heristics = {"random":200,"NGOpt":0,"GA":0, "PSO":0,"DE":0},
        max_acq_size=256,
        verbose=True,
        use_ard=True,
        max_cholesky_size=800,
        n_training_steps=100,
        min_cuda=1024,
        device="cpu",
        dtype="float64",
        seed = None,
        initial_guess=None,
    ):

        # Basic input checks
        assert budget > 0 and isinstance(budget, int)
        assert batch_size > 0 and isinstance(batch_size, int)
        assert n_init > 0 and isinstance(n_init, int)
        assert max_acq_size > 0 and isinstance(max_acq_size, int)
        assert isinstance(verbose, bool) and isinstance(use_ard, bool)
        assert max_cholesky_size >= 0 and isinstance(batch_size, int)
        assert n_training_steps >= 30 and isinstance(n_training_steps, int)
        assert budget > n_init and budget > batch_size
        assert device == "cpu" or device == "cuda"
        assert dtype == "float32" or dtype == "float64"
        if device == "cuda":
            assert torch.cuda.is_available(), "can't use cuda if it's not available"

        self.fun=fun
        self.gen_ir_fun=fun.gen_optIR
        self.build_fun = fun.build
        self.eval_fun = fun.measure
        self.tmp_dir=fun.tmp_dir
        self.passes=passes
        # self.pass2num={}
        # i=0
        # for p in range(len(self.passes)):
        #     self.pass2num[p]=i
        #     i += 1
        
        
        self.len_seq=len_seq
        self.n_init = n_init
        self.n_evals = 0
        self.budget = budget
        self.batch_size = batch_size
        self.heristics = heristics
        self.acqf=acqf
        self.max_acq_size = max_acq_size
        self.verbose = verbose
        self.use_ard = use_ard
        self.max_cholesky_size = max_cholesky_size
        self.n_training_steps = n_training_steps
        self.min_cuda = min_cuda
        self.beta = beta
        self.ga_pop_size=50
        self.n_parallel = n_parallel
        self.max_cand_seqs=max_cand_seqs
        
        
        

        # Save the full history
        self.params_list, self.fX = [], []
        self.best_y = inf
        
        self.cands= {}
        for filename in self.fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            self.cands[fileroot]=[]
        
        
        self.new_seqs= []
        self.seq_next, self.fX_next = '', inf
        
        
        
        self.failcount = 0
        self.succcount = 0
        self.failtol = 2000

        self.initialization = True


        # Device and dtype for GPyTorch
        self.dtype = torch.float32 if dtype == "float32" else torch.float64
        self.device = torch.device("cuda") if device == "cuda" else torch.device("cpu")


        # params = ng.p.Choice(
        #         choices=self.passes,
        #         repetitions=len_seq,
        #         deterministic=True
        #     )
        
        # # self.NGOpt = ng.optimizers.NGOpt(parametrization=params, budget=self.budget)
        # self.PSO=ng.optimizers.PSO(parametrization=params, budget=self.budget)
        # self.DE=ng.optimizers.DE(parametrization=params, budget=self.budget)
        
        # self.GA = None
        
        self.initial_guess=initial_guess
        
        if seed is not None:
            self.seed = seed
        else:
            self.seed = np.random.randint(1e5)
    
    
    
    def _update_failcount(self, fX_next):
        if np.min(fX_next) < np.min(self.fX) - 1e-3 * math.fabs(np.min(self.fX)):
            self.failcount = 0
            self.succcount +=1
        else:
            self.failcount += self.batch_size
            self.succcount = 0
            
        if self.succcount == 3:
            self.length = min([2.0 * self.length, 0.5])
            self.succcount = 0
        if self.failcount > self.failtol:
            self.length /= 2   
            
    
    
        
    def ask(self):
        
        if len(list(self.cands.values())[0]) > self.max_cand_seqs:
            return None
            # for key, value in self.heristics.items():
            #     self.heristics[key] = 1
        
        new_cands= {}
        for filename in self.fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            new_cands[fileroot]=[]
            for _ in range(self.heristics['random']):
                seq=random.choices(self.passes, k=self.len_seq)
                seq=check_seq(seq)
                if seq not in self.cands[fileroot]:
                    new_cands[fileroot].append(' '.join(seq))
        
        
        # for _ in range(self.heristics['DE']):
        #     u = self.DE.ask()
        #     seq=list(u.value)
        #     seq=self.check_seq(seq)
        #     if seq not in seqs:
        #         seqs.append(' '.join(seq))
        # for _ in range(self.heristics['PSO']):
        #     u = self.PSO.ask()
        #     seq=list(u.value)
        #     seq=self.check_seq(seq)
        #     if seq not in seqs:
        #         seqs.append(' '.join(seq))

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
            
        # def worker(seq, return_dict):
        #     return_dict[seq] = self.gen_ir_fun(seq)
        
        # return_dict = Manager().dict()
        # procs = []
        
        # for seq in new_cand_seqs:
        #     p = Process(target=worker, args=(seq,  return_dict))
        #     procs.append(p)
        
        # chunked_procs_list = []
        # for i in range(0, len(procs), self.n_parallel):
        #     chunked_procs_list.append(procs[i:i+self.n_parallel])
        # for chunked_procs in chunked_procs_list:
        #     for p in chunked_procs:
        #         p.start()
        #     for p in chunked_procs:
        #         p.join()

        # new_seqs = []
        
        # for seq in new_cand_seqs:
        #     if return_dict[seq]:
        #         new_seqs.append(seq)
        #     else:
        #         print('failed compilation')
        
        # return  new_seqs
    
    
    
    def train_gp(self, _X, _fX, hypers={}):
        '''
        X (list):
        fX:
        '''
        t0 = time()
       
        X = np.array(_X)
        fX = np.expand_dims(np.array(_fX), axis=1)
        # Figure out what device we are running on
        if len(X) < self.min_cuda:
            device, dtype = torch.device("cpu"), torch.float64
        else:
            device, dtype = self.device, self.dtype
        
        # if (fX>0).all():
        #     # self.pt=PowerTransformer(method='box-cox')
        #     # self.pt.fit(fX)
        #     # y=self.pt.transform(fX)
        #     y=power_transform(fX,method='box-cox')
        # else:
        #     # self.pt=PowerTransformer(method='yeo-johnson')
        #     # self.pt.fit(fX)
        #     # y=self.pt.transform(fX)
        #     y=power_transform(fX,method='yeo-johnson')
        
        y=(fX-fX.mean())/fX.std() #change
        
        X_torch = torch.tensor(X).to(device=device, dtype=dtype)
        y_torch = torch.tensor(y).to(device=device, dtype=dtype)
        self.train_y=-y_torch
        self.train_x=X_torch
        
        
        
        with gpytorch.settings.max_cholesky_size(self.max_cholesky_size), gpytorch.settings.max_cg_iterations(2000):
                # botorch by default is for maxmizing the objective function
                self.gp = train_gp(
                    train_x=self.train_x, train_y = self.train_y, use_ard=self.use_ard, use_input_warping=False, num_steps=self.n_training_steps, lr=0.1
                )
        
        # Remove the torch variables
        del X_torch, y_torch
        hypers = self.gp.state_dict()
        if self.verbose:
            print("Training cost {:.4f}".format(time()-t0))
        return self.gp, hypers
    
    
    def predict(self, gp_model, cand_X):
        """Select candidates."""
        t0 = time()
        # We may have to move the GP to a new device
        # device=torch.device("cpu")
        gp_model = gp_model.to(dtype=self.dtype, device=self.device)
        if self.acqf =='EI':
            acqf = qExpectedImprovement(gp_model, self.train_y.max().to(dtype=self.dtype, device=self.device))
            # acqf = qNoisyExpectedImprovement(gp_model, self.train_x.to(dtype=self.dtype, device=self.device))
        else:
            acqf = qUpperConfidenceBound(gp_model, beta=self.beta)
       
        X= np.array(deepcopy(cand_X))
        with torch.no_grad(), gpytorch.settings.fast_pred_var(), gpytorch.settings.fast_pred_samples():
            if len(X) > self.max_acq_size:
                cands_list = np.array_split(X, np.ceil(len(X)/self.max_acq_size))
            else:
                cands_list = [X]
            y = np.zeros((0,1))
            for X in cands_list:
                X_cand_torch = torch.tensor(X).to(device=self.device, dtype=self.dtype)
                y_cand_torch = acqf(X_cand_torch.unsqueeze(-2))
                y_tmp = y_cand_torch.detach().cpu().numpy().reshape(-1, 1)
                y=np.vstack((y, y_tmp))
        acq_values = y.ravel()
        if self.verbose:
            print("Predicting cost {:.4f}".format(time()-t0))
        return acq_values
    
    
    def select_and_eval(self, acq_values, cand_params):
        index = np.argmax(acq_values)
        params_next = cand_params[index]
        fX_next = self.fun(params_next)
        return params_next, fX_next
        

    
    
    
    
        
    def tell(self, params_next, fX_next):
        self.n_evals += 1
        self.fX.append(fX_next)
        self.params_list.append(params_next)
        self.best_params = self.params_list[np.argmin(self.fX)]
        self.best_y=np.min(self.fX)
        
        # update heristics
        # nevergrad_heristics=['DE', 'PSO']
        # for h in nevergrad_heristics:
        #     optimizer = getattr(self, h)
        #     if self.heristics[h] >0:
        #         optimizer.suggest(seq_next.split())
        #         cand = optimizer.ask()
        #         optimizer.tell(cand, fX_next)
        
        # update training samples and write to log
        # self.seqs.append(seq_next)
        
        # data = [seq_next, fX_next]
        # with open(self.result_file, 'a') as f:
        #     f.write(json.dumps(data)+'\n')
        
        # with open(self.plot_file, 'w') as f:
        #     f.write(json.dumps(self.fX))
        
        # self.best_seq = self.seqs[np.argmin(self.fX)]
        # self.best_y = min(self.fX)
        # data = [self.best_seq, self.best_y]
        # with open(self.best_result_file, 'w') as f:
        #     f.write(json.dumps(data)+'\n')
        
        # update candidates and write to log
        # new_cand_seqs = []
        # for seq in new_seqs:
        #     new_cand_seqs.append(seq)
        # self.cand_seqs += new_cand_seqs
        # self.cand_seqs = list(set(self.cand_seqs))
        # if seq_next in self.cand_seqs:
        #     self.cand_seqs.remove(seq_next)
        
        # with open(self.cand_file, 'a') as f:
        #     f.write(json.dumps(data)+'\n')
    
    
    
    
    # def params2vec(self, params):
    #     x = []
    #     for fileroot, seq in params.items():
    #         vec = self.seq2vec[fileroot][seq]
    #         x.append(vec)
    #     x = np.array(x).flatten()
    #     return x
    
    # @staticmethod
    def cands2vecs(self, cands):
        vecs_dict = {}
        feature_names=[]
        for fileroot, seqs in cands.items():
            cfg_json_list=[]
            for seq in seqs:
                cfg={}
                cfg['tmp_dir']=self.tmp_dir
                cfg['params']={}
                cfg['params'][fileroot]=seq
                cfg_json=json.dumps(cfg)
                cfg_json_list.append(cfg_json)
            t0 = time()
            stats_list = read_optstats_from_cfgjsonlist(cfg_json_list)
            x = zip(stats_list, seqs)
            filtered_stats, filtered_seqs = zip(*[(stat, seq) for stat, seq in zip(stats_list, seqs) if stat is not None])
            seqs = list(filtered_seqs)
            stats_list = list(filtered_stats)
            cands[fileroot] = seqs


            # fixme: check failed seqs
            # print("read_optstats_from_cfgjsonlist cost {:.4f}".format(time()-t0))
            t0 = time()
            X, feature_names0 = stats2vec(stats_list)
            # print("stats2vec cost {:.4f}".format(time()-t0))
            vecs_dict[fileroot] = X
            feature_names.extend(feature_names0)
        return cands, vecs_dict, feature_names
    
    def feature_extraction(self):
        # extract features
        t0 = time()
        self.cands, self.vecs_dict, self.feature_names = self.cands2vecs(self.cands)
        self.seq2vec = {}
        for fileroot in self.cands:
            self.seq2vec[fileroot] = dict(zip(self.cands[fileroot],self.vecs_dict[fileroot]))
        if self.verbose:
            print("Feature_extraction cost {:.4f}".format(time()-t0))
        return self.seq2vec


    def minimize(self):
        """Run the full optimization process."""
        
        epochs=0
        self.failcount = 0
        
        # firstly build the program in '-O3'
        assert self.build_fun('-O3')
        
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
            seq=random.choices(self.passes, k=self.len_seq)
            seq=check_seq(seq)
            params={}
            for filename in self.fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                opt_str=' '.join(seq)
                params[fileroot]=opt_str
                if opt_str not in self.cands[fileroot]:
                    self.cands[fileroot].append(opt_str)
            if params not in initial_params_list:
                initial_params_list.append(params)
            
        
        
        print('len_init_samples:',len(initial_params_list))
        
        for params in initial_params_list:
            fX_next = self.fun(params)
            if fX_next != inf:
                self.tell(params, fX_next)
                
            
                

            
        
        


        
        # print('cost time:', time()-t0)
        new_cands = self.ask()
        if new_cands is not None:
            self.genIR_and_update(new_cands)
            new_cands, _, _ = self.cands2vecs(new_cands)
            for fileroot in self.cands:
                self.cands[fileroot].extend(new_cands[fileroot])
        self.feature_extraction()
        while self.n_evals < self.budget:
            
            # ask new candidates
            new_cands = self.ask()
            
            if new_cands is not None:
                # generate optimized IRs parallely and update
                self.genIR_and_update(new_cands)
                new_cands, _, _ = self.cands2vecs(new_cands)
                for fileroot in self.cands:
                    self.cands[fileroot].extend(new_cands[fileroot])
                # extract features
                self.feature_extraction()


            # prepare candidates for the next evaluation
            if self.n_evals <200:
                k = 200 #later
            else:
                k = 100
            n_cands=len(list(self.cands.values())[0])
            if k > n_cands:
                k = n_cands
            
            
            cand_params_list = []
            t0=time()
            # fileroot = random.choice(list(self.cands.keys()))
            # if new_cands is not None:
            #     seqs = new_cands[fileroot] + random.sample(self.cands[fileroot], k=k)
            # else:
            #     seqs = random.sample(self.cands[fileroot], k=k)
            # for seq in seqs:
            #     params = permu_best(self.best_params, fileroot, seq)
            #     if params not in self.params_list:
            #         cand_params_list.append(params)

            for fileroot in self.cands:
                if new_cands is not None:
                    seqs = new_cands[fileroot] + random.sample(self.cands[fileroot], k=k)
                else:
                    seqs = random.sample(self.cands[fileroot], k=k)
                for seq in seqs:
                    params = permu_best(self.best_params, fileroot, seq)
                    if params not in self.params_list:
                        cand_params_list.append(params)
                    
                # with Pool() as p:
                #     perm_params_list_single = p.starmap(permu_best, itertools.product([self.best_params],[fileroot], seqs))
                # cand_params_list.extend(perm_params_list_single) #later
            print('permu_best cost:',time()-t0)
            
            
            
            
            
            
            
            
            t0 = time()
            ff=params2vec(self.seq2vec)
            cand_X=[]
            for params in cand_params_list:
                cand_X.append(ff(params))
            self.X=[]
            for params in self.params_list:
                self.X.append(ff(params))

            
            # with Pool() as p:
            #     cand_X = p.map(params2vec(self.seq2vec), cand_params_list)

            # with Pool() as p:
            #     self.X = p.map(params2vec(self.seq2vec), self.params_list)
            if self.verbose:
                print('params2vec cost:',time()-t0)
             


            # train GP
            self.gp, _= self.train_gp(self.X, self.fX)
            
            # lengthscales = self.gp.covar_module.base_kernel.lengthscale.cpu().squeeze()
            # dd = dict(zip(feature_names, lengthscales))
            # for iii in lengthscales.argsort()[:20]:
            #     print(feature_names[iii], lengthscales[iii].item())
            
            
            # predict acqf values
            acq_values = self.predict(self.gp, cand_X)
            
            # if there are candidates with unexplored features, we explore them
            X_mean = np.mean(np.array(self.X), axis=0)
            inds=[]
            unexplored_feature_names=[]
            for i in range(len(X_mean)):
                if X_mean[i]==0:
                    inds.append(i)
                    unexplored_feature_names.append(self.feature_names[i])
                    # print(self.feature_names[i])     
            # print(unexplored_feature_names)
            print('Num of unexplored features:',len(unexplored_feature_names))
            mask = nonzero_rows(np.array(cand_X), inds) #later
            # acq_values[mask] = acq_values[mask] + 1000
            if np.random.rand() > 0.5:
                acq_values[mask] = acq_values[mask] + 1000
            
            
            # select one sample from all candidates and evaluate them
            params_next, fX_next = self.select_and_eval(acq_values, cand_params_list)
            for fileroot in params_next:
                if params_next[fileroot] != self.best_params[fileroot]:
                    print(fileroot)
                    
            # update heristics
            self.tell(params_next, fX_next)
            
            # # record 
            # self.record()
            
            
            #Avoid OOM
            gc.collect()
            torch.cuda.empty_cache()  
            
        # print final results
        # print('results are saved to {}', self.result_file)
        # print('the best reult are saved to {}', self.best_result_file)
            

                



                


import time
import argparse
from math import inf
import subprocess
import json
import re
import os
import glob
import nevergrad as ng
from multiprocessing import Pool

import llvmtuner
from llvmtuner import searchspace
from llvmtuner.BO.BO import BO
from llvmtuner.baselines.random import random_optimizer
from llvmtuner.baselines.nevergrad import nevergrad_optimizer
from llvmtuner.function_wrap import Function_wrap
from llvmtuner.gen_hotfiles import gen_hotfiles


parser = argparse.ArgumentParser()
parser.add_argument('--method', required=True, help='')
parser.add_argument('--benchmark', required=True, help='')
parser.add_argument('--budget', type=int,default=50, help='')
parser.add_argument('--n-parallel', type=int,default=50, help='')
parser.add_argument('--batch-size', type=int, default=1)
args = parser.parse_args()

passes=llvmtuner.searchspace.default_space()[0]

benchmarks = ['510.parest_r', '511.povray_r', '519.lbm_r', '505.mcf_r', '520.omnetpp_r', '523.xalancbmk_r', '531.deepsjeng_r', '541.leela_r', '557.xz_r', '508.namd_r', '538.imagick_r', '544.nab_r']

# pre_buildsetup_cmd = f'runcpu --action buildsetup --size train --config my-clang-linux-x86.cfg --define SPECLANG="clangopt" --define SPECLANGXX="clangxxopt" {args.benchmark}'
# subprocess.run(pre_buildsetup_cmd, shell=True)
build_cmd = f'runcpu --action build --size train --config my-clang-linux-x86.cfg --define SPECLANG="clangopt" --define SPECLANGXX="clangxxopt" {args.benchmark}'
build_dir = f'/home/jiayu/cpu2017/benchspec/CPU/{args.benchmark}/exe/'

tmp_dir = os.path.join(os.path.expanduser('~/local_result_llvmtuner_17/SPEC/'), args.benchmark, args.method)
run_dir = os.path.expanduser(f'~/spec2017_run/{args.benchmark}')
run_cmd = f'./run_{args.benchmark}.sh'
_ , binary0 = args.benchmark.split('.')
binary_name = binary0 + '_base.llvmtuner17.0.6'
binary = os.path.join(build_dir, binary_name)

fun = Function_wrap(
                    build_cmd=build_cmd, #编译命令，用户提供
                    build_dir=build_dir, #编译路径，用户提供
                    tmp_dir=tmp_dir, #数据存放目录，用户定义
                    run_cmd=run_cmd, #运行命令，用户提供
                    run_dir=run_dir, #运行路径，用户提供
                    binary=binary, #编译后的二进制文件路径，用户提供
                    )
fun.repeat = 1 
fun.adaptive_measure = False

t0=time.time()
print('-----------------build -O3-----------------')
fun.build('default<O3>')
print('O3 compilation time:',time.time()-t0)

if __name__ == "__main__":
    if args.method=='random': 
        optimizer=random_optimizer(fun=fun, passes=passes, budget=args.budget)
        best_cfg, best_cost = optimizer.minimize()
        print('best runtime:', best_cost)
    
    if args.method=='nevergrad':
        optimizer=nevergrad_optimizer(fun=fun, passes=passes, budget=args.budget)
        best_cfg, best_cost = optimizer.minimize()
        print('best runtime:', best_cost)
    
    if args.method=='BO':
        BO=BO(
                fun=fun,
                passes=passes, 
                budget=args.budget, 
                acqf='EI',
                n_init=5,
                max_cand_seqs = 200,
                device='cpu',
                )
        BO.minimize()

    if args.method=='O3':
        y = fun('default<O3>')
        print('O3 runtime:', y)


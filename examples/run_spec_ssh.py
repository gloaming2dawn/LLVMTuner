import time
import random as random
from multiprocessing import Pool
from fabric import Connection
import invoke
import argparse
from math import inf
import subprocess
import json
import re
import os
import nevergrad as ng
import glob
import numpy as np
from copy import deepcopy

import llvmtuner
from llvmtuner import searchspace
from llvmtuner.feature_extraction import read_optstats_from_cfgpathlist,read_optstats_from_cfgjsonlist,stats2vec
from llvmtuner.BO.BO import BO
from llvmtuner.function_wrap import Function_wrap


parser = argparse.ArgumentParser()
parser.add_argument('--device', required=True, help='')
parser.add_argument('--method', required=True, help='')
parser.add_argument('--benchmark', required=True, help='')
parser.add_argument('--budget', type=int,default=50, help='')
parser.add_argument('--n-parallel', type=int,default=50, help='')
parser.add_argument('--batch-size', type=int, default=1)
args = parser.parse_args()

passes=llvmtuner.searchspace.default_space()

benchmarks = ['505.mcf_r', '520.omnetpp_r', '523.xalancbmk_r', '531.deepsjeng_r', '541.leela_r', '557.xz_r', '508.namd_r', '510.parest_r', '511.povray_r', '519.lbm_r', '538.imagick_r', '544.nab_r']

host="nvidia@TX2-{}.local".format(args.device)
sshC=Connection(host=host)


ccmd = f'runcpu --action build --size train --config my-clang-linux-cross_x862aarch64.cfg --define SPECLANG="clangopt" {args.benchmark}'
ben_dir = f'/home/jiayu/cpu2017/benchspec/CPU/{args.benchmark}/exe/'
tmp_dir = os.path.join(os.path.expanduser('~/result_llvmtuner_v5/SPEC/'), args.benchmark, args.method)

def run_and_eval_fun():
    _ , binary = args.benchmark.split('.')
    binary = binary + '_base.mytest'
    run_dir = f'/home/nvidia/spec2017_run/{args.benchmark}'
    try:
        ret = sshC.put(local=os.path.join(ben_dir, binary), remote=run_dir)
    except Exception as e:
        assert 1==0

    os.remove(os.path.join(ben_dir, binary))

    
    
    myscript = f'run_{args.benchmark}.sh'
    run_cmd = f'time ./{myscript}'
    try:
        with sshC.cd(run_dir):
            ret=sshC.run(run_cmd, hide=True, timeout=100)
        temp=ret.stderr.strip()
        real=temp.split('\n')[-3]
        searchObj = re.search( r'real\s*(.*)m(.*)s.*', real)
        runtime = int(searchObj[1])*60+float(searchObj[2])
    except invoke.exceptions.UnexpectedExit:
        runtime = inf
    except invoke.exceptions.CommandTimedOut:
        runtime = inf
    return runtime 

fun = Function_wrap(ccmd, ben_dir, tmp_dir, run_and_eval_fun)
len_seq=100

def check_seq(seq):
    cgprofile_count = seq.count('-cg-profile')
    if cgprofile_count>1:
        for _ in range(cgprofile_count-1):
            index = seq.index('-cg-profile')
            seq[index] = ''
            # seq.remove('-cg-profile')
            # seq.append('-inline')
    
    for i in range(len(seq) - 1):
        if seq[i] == seq[i + 1]:
            seq[i + 1] = ''
    return seq

if args.method=='one-for-all': 
    for i in range(args.budget):
        seq=random.choices(passes, k=len_seq)
        seq=check_seq(seq)
        y = fun(' '.join(seq))



if args.method=='random': 
    params_list=[]
    for _ in range(args.budget):
        seq=random.choices(passes, k=len_seq)
        seq=check_seq(seq)
        params={}
        for filename in fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            params[fileroot]=' '.join(seq)
        params_list.append(params)

    t0 = time.time()
    with Pool(50) as p:
        flags = p.map(fun.genoptIR, params_list)
    print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
    
    for i in range(len(params_list)):
        y = fun(params_list[i])


if args.method=='nevergrad':
    import nevergrad as ng
    import numpy as np
    params = ng.p.Choice(
            choices=passes,
            repetitions=len_seq,
            deterministic=True
        )
    optimizer=ng.optimizers.NGOpt(parametrization=params, budget=args.budget)
    print(optimizer._select_optimizer_cls())
    for i in range(args.budget):
        x = optimizer.ask()
        seq=list(x.value)
        seq=check_seq(seq)
        
        y=fun(' '.join(seq))
        if y != inf:
            optimizer.tell(x, y)
        
if args.method=='BO':
    BO=BO(
        fun=fun,
        passes=passes, 
        len_seq=len_seq,
        budget=args.budget, 
        acqf='EI',
        # beta=1.96,
        n_parallel=args.n_parallel,
        n_init=20,
        )

    BO.minimize()
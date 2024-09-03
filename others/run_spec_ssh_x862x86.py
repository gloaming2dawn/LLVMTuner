import time
import hashlib
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
from llvmtuner.searchspace import default_space, passlist2str, parse_O3string
from llvmtuner.feature_extraction import read_optstats_from_cfgpathlist,read_optstats_from_cfgjsonlist,stats2vec
from llvmtuner.BO.BO import BO
from llvmtuner.BO.Adalocaloptimizer import Adalocaloptimizer
from llvmtuner.BO.Localoptimizer import Localoptimizer
from llvmtuner.function_wrap import Function_wrap
from llvmtuner.gen_hotfiles import perf_record, gen_hotfiles
from llvmtuner.show_features import read_json_lines


parser = argparse.ArgumentParser()
parser.add_argument('--method', required=True, help='')
parser.add_argument('--benchmark', required=True, help='')
parser.add_argument('--budget', type=int,default=50, help='')
parser.add_argument('--n-parallel', type=int,default=50, help='')
parser.add_argument('--batch-size', type=int, default=1)
args = parser.parse_args()

passes=llvmtuner.searchspace.default_space()

benchmarks = ['505.mcf_r', '520.omnetpp_r', '523.xalancbmk_r', '531.deepsjeng_r', '541.leela_r', '557.xz_r', '508.namd_r', '510.parest_r', '511.povray_r', '519.lbm_r', '538.imagick_r', '544.nab_r']

host="jiayu@dss4090.local"
sshC=Connection(host=host)


ccmd = f'runcpu --action build --size test --config my-clang-linux-x86.cfg --define SPECLANG="clangopt" --define SPECLANGXX="clangxxopt" {args.benchmark}'
ben_dir = f'/home/jiayu/cpu2017/benchspec/CPU/{args.benchmark}/exe/'
tmp_dir = os.path.join(os.path.expanduser('~/result_llvmtuner_17/SPEC/'), args.benchmark, args.method)
run_dir = f'/home/jiayu/spec2017_run/{args.benchmark}'
run_cmd = f'./run_{args.benchmark}.sh'
_ , binary = args.benchmark.split('.')
binary_name = binary + '_base.llvmtuner17.0.6'

def run_and_eval_fun():
    _ , binary = args.benchmark.split('.')
    binary = binary + '_base.llvmtuner17.0.6'
    run_dir = f'/home/jiayu/spec2017_run/{args.benchmark}'
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
fun.repeat = 1
fun.adaptive_measure = False
# t0=time.time()
# print('-----------------build -O3-----------------')
# fun.build('default<O3>')
# print('O3 compilation time:',time.time()-t0)

len_seq=120

if args.method == 'O3':
    y = fun('default<O3>')

if args.method == 'perf':
    module2funcnames = fun._get_func_names()
    print(module2funcnames)
    # fun('default<O3>')#
    folded_perf_result = perf_record(sshC, ben_dir, run_dir, run_cmd)
    print(folded_perf_result)
    hotfiles,hotfiles_details = gen_hotfiles(module2funcnames, binary_name, folded_perf_result)
    print(hotfiles, hotfiles_details)
    with open(f'{args.benchmark}_hotfiles.json','w') as file:
        json.dump(hotfiles_details, file, indent=4)


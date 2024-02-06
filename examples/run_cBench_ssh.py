# -*- coding: utf-8 -*-
"""
Created on Wed Mar  2 17:54:48 2022

@author: scjzhadmin
"""
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
from llvmtuner.gen_hotfiles import perf_record, gen_hotfiles



parser = argparse.ArgumentParser()
parser.add_argument('--device', required=True, help='')
parser.add_argument('--method', required=True, help='')
parser.add_argument('--benchmark', required=True, help='')
parser.add_argument('--budget', type=int,default=50, help='')
parser.add_argument('--n-parallel', type=int,default=50, help='')
parser.add_argument('--batch-size', type=int, default=1)
args = parser.parse_args()

passes, O3_trans_seq=llvmtuner.searchspace.default_space()
# passes=llvmtuner.searchspace.compilergym_space()
passes.append('')



# 热点在IR不值得优化: security_rijndael_d security_rijndael_e consumer_jpeg_d consumer_tiff2rgba consumer_tiff2bw consumer_tiffdither
# IO噪声大: consumer_jpeg_c

ben2num={'automotive_bitcount':5, 'automotive_qsort1': 10,'automotive_susan_c':50, 'automotive_susan_e':20, 'automotive_susan_s':5,'bzip2d':3,'bzip2e':2,'consumer_jpeg_c':100,'consumer_lame':10, 'consumer_tiffmedian':200,'network_dijkstra':100000,'network_patricia':5000,'security_blowfish_d':5000, 'security_blowfish_e':5000, 'security_sha':8000, 'telecom_adpcm_c':500,'telecom_adpcm_d':1000, 'telecom_CRC32':50, 'telecom_gsm':20, 'consumer_jpeg_d':30, 'consumer_tiff2bw':100, 'consumer_tiff2rgba':30, 'office_stringsearch1': 100000} 

ben2hot={'automotive_bitcount': ['bitcnts', 'bitcnt_4', 'bitcnt_3', 'bitcnt_2'], 'automotive_qsort1': ['qsort', 'qsort_large'], 'automotive_susan_c': ['susan'], 'automotive_susan_e': ['susan'], 'automotive_susan_s': ['susan'], 'bzip2d': ['bzlib', 'decompress'], 'bzip2e': ['blocksort', 'compress', 'bzlib'], 'consumer_jpeg_c': ['jcphuff', 'jcdctmgr', 'jfdctint', 'jccolor', 'jchuff', 'jccoefct'], 'consumer_jpeg_d': ['jidctint', 'jdhuff', 'jdcolor', 'jdsample'], 'consumer_lame': ['psymodel', 'newmdct', 'fft', 'quantize', 'quantize-pvt', 'l3bitstream', 'formatBitstream'], 'consumer_tiff2bw': ['tif_lzw', 'tif_predict', 'tif_dirread', 'tif_dir'], 'consumer_tiff2rgba': ['tif_lzw', 'tif_getimage', 'tif_predict'], 'consumer_tiffmedian': ['tiffmedian'], 'network_dijkstra': ['dijkstra_large'], 'network_patricia': ['patricia'], 'office_stringsearch1': ['pbmsrch_large'], 'security_blowfish_d': ['bf_enc', 'bf_cfb64'], 'security_blowfish_e': ['bf_enc', 'bf_cfb64'], 'security_sha': ['sha'], 'telecom_CRC32': ['crc_32'], 'telecom_adpcm_c': ['adpcm'], 'telecom_adpcm_d': ['adpcm'], 'telecom_gsm': ['long_term', 'short_term', 'preprocess', 'rpe', 'lpc']}

final_benchmarks=[]
for benchmark in ben2hot:
    if len(ben2hot[benchmark])>1:
        final_benchmarks.append(benchmark)
# print(final_benchmarks)

for key, value in ben2hot.items():
    ben2hot[key] = [v + '.c' for v in value]

ben_dir = os.path.expanduser('~/cBench_V1.1/{}/src_work/'.format(args.benchmark))
cross_flags='--target=aarch64-linux-gnu --sysroot=/home/jiayu/gcc-4.8.5-aarch64/install/aarch64-unknown-linux-gnu/sysroot/ --gcc-toolchain=/home/jiayu/gcc-4.8.5-aarch64/install'
ccmd = f'make ZCC=clangopt LDCC=clangopt CCC_OPTS="{cross_flags}" LD_OPTS="{cross_flags}" -C {ben_dir}'
ccmd_g = f'make ZCC=clangopt LDCC=clangopt CCC_OPTS="{cross_flags} -g" LD_OPTS="{cross_flags} -g" -C {ben_dir}'

tmp_dir = os.path.join(os.path.expanduser('~/result_llvmtuner_v5/cBench/'), args.benchmark, args.method)
binary_name = 'a.out'

host="nvidia@TX2-{}.local".format(args.device)
sshC=Connection(host=host)

run_dir = '/home/nvidia/cBench_V1.1/{}/src_work/'.format(args.benchmark)
run_cmd = './__run 1 {}'.format(ben2num[args.benchmark])

def run_and_eval_fun():
    try:
        ret = sshC.put(local=os.path.join(ben_dir,'a.out'), remote=run_dir)
    except Exception as e:
        try:
            ret = sshC.put(local=os.path.join(ben_dir,'a.out'), remote=run_dir)
        except Exception as e:
            try:
                ret = sshC.put(local=os.path.join(ben_dir,'a.out'), remote=run_dir)
            except Exception as e:
                assert 1==0, [os.path.join(ben_dir,'a.out'), run_dir]

    try:
        timeout_seconds = 5
        with sshC.cd(run_dir):
            ret=sshC.run(f'timeout {timeout_seconds} '+run_cmd, hide=True, timeout=timeout_seconds)
        temp=ret.stderr.strip()
        real=temp.split('\n')[-3]
        searchObj = re.search( r'real\s*(.*)m(.*)s.*', real)
        runtime = int(searchObj[1])*60+float(searchObj[2])
    except invoke.exceptions.UnexpectedExit:
        runtime = inf
    except invoke.exceptions.CommandTimedOut:
        runtime = inf
        # kill_command = f"kill {remote_process_pid}"
        # sshC.run(kill_command)
    return runtime 



allfiles=[]
files=glob.glob(os.path.join(ben_dir,'*.c'))
for f in files:
    fName = f.split('/')[-1]
    fileroot,fileext=os.path.splitext(fName)
    allfiles.append(fName)



fun_O3 = Function_wrap(ccmd_g, ben_dir, tmp_dir, run_and_eval_fun, hotfiles=allfiles)
t0=time.time()
print('-----------------build -O3-----------------')
fun_O3.build('-O3')
print('O3 compilation time:',time.time()-t0)
# fun_O3('-O3')

# module2funcnames = fun_O3._get_func_names()
# folded_perf_result = perf_record(sshC, ben_dir, run_dir, run_cmd)
# hotfiles = gen_hotfiles(module2funcnames, binary_name, folded_perf_result)
# print(hotfiles)

hotfiles=ben2hot[args.benchmark]

f = Function_wrap(ccmd, ben_dir, tmp_dir, run_and_eval_fun, hotfiles)#, profdata=os.path.join(ben_dir, 'default.profdata')

fun=f
len_seq=150


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

    
if __name__ == "__main__":
    if args.method == 'O1':
        f.hotfiles =allfiles
        y = fun('-O1')
    
    if args.method == 'O2':
        f.hotfiles =allfiles
        y = fun('-O2')
    
    if args.method == 'O3_seq':
        f.hotfiles =allfiles
        y = fun(' '.join(O3_trans_seq))

    if args.method == 'O3':
        f.hotfiles =allfiles
        y = fun('-O3')
        # y = f("-mem2reg -div-rem-pairs -jump-threading -loop-unswitch -sroa -indvars -loop-rotate -instcombine -globalopt -tailcallelim -loop-idiom -loop-unroll -function-attrs -loop-deletion")
        # y = f("-mem2reg -div-rem-pairs -jump-threading -loop-unswitch -sroa -indvars -loop-rotate -instcombine -globalopt -tailcallelim -loop-idiom -loop-unroll -functionattrs -loop-deletion")
    
    if args.method == 'O3-random':
        def random_params():
            params={}
            for filename in fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                seq=random.choices(passes, k=len_seq)
                seq=check_seq(seq)
                params[fileroot]='-O3 ' + ' '.join(seq)
            return params
        
        params_list = []
        for _ in range(args.budget):
            params = random_params()
            params_list.append(params)
        
        t0 = time.time()
        with Pool(50) as p:
            flags = p.map(fun.gen_optIR, params_list)
        print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        
        for i in range(len(params_list)):
            if flags[i]:
                y = fun(params_list[i])
        
        print(f'{args.benchmark} {args.budget} iterations cost:',time.time()-t0)


    if args.method=='random':
        def random_params():
            params={}
            for filename in fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                seq=random.choices(passes, k=len_seq)
                seq=check_seq(seq)
                params[fileroot]=' '.join(seq)
            return params
        
        params_list = []
        for _ in range(args.budget):
            params = random_params()
            params_list.append(params)
        
        t0 = time.time()
        with Pool(50) as p:
            flags = p.map(fun.gen_optIR, params_list)
        print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        
        for i in range(len(params_list)):
            if flags[i]:
                y = fun(params_list[i])
        
        print(f'{args.benchmark} {args.budget} iterations cost:',time.time()-t0)
        
            
            
    if args.method=='one-for-all-random': 
        def random_params_one():
            seq=random.choices(passes, k=len_seq)
            seq=check_seq(seq)
            params={}
            for filename in fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                params[fileroot]=' '.join(seq)
            return params
        
        params_list=[]
        for _ in range(args.budget):
            params = random_params_one()
            params_list.append(params)
            # y = f(' '.join(seq))
        
        t0 = time.time()
        with Pool(50) as p:
            flags = p.map(fun.gen_optIR, params_list)
        print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        
        for i in range(len(params_list)):
            if flags[i]:
                y = fun(params_list[i])
        print(f'{args.benchmark} {args.budget} iterations cost:',time.time()-t0)



    if args.method=='one-by-one':
        params={}
        for filename in fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            params[fileroot] = '-O3'
        y = fun(params)

        for filename in fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            params=deepcopy(fun.best_params)
            for _ in range(args.budget):
                seq=random.choices(passes, k=len_seq)
                seq=check_seq(seq)
                params[fileroot]=' '.join(seq)
                y = fun(deepcopy(params))
            
            
                
        
                
        
    
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

    
        
        
    if args.method == 'reduce':
        dirname=os.path.expanduser('~/cBench_result')
        file=os.path.join(dirname,'best.json')
        with open(file,'r') as ff:
            data=json.load(ff)
            x_best, y_best, y_O3=data[args.benchmark]
        print(args.benchmark, y_best, y_O3, y_O3/y_best)
        
        
        # dirname=os.path.expanduser('~/cBench_result')
        # file=os.path.join(dirname,f'{args.benchmark}_reduce_best.json')
        # with open(file,'r') as ff:
        #     data=json.load(ff)
        # x_best, y_best, y_O3=data[args.benchmark]
        # print('after reduce: ',args.benchmark, x_best, y_best, y_O3, y_O3/y_best)
        
        # if args.benchmark == 'consumer_lame':
        #     x_best='-gvn -loop-rotate -break-crit-edges -inline -sroa -reassociate -simplifycfg -loop-rotate -partial-inliner -licm -instsimplify -lcssa -inferattrs -gvn -loop-vectorize -jump-threading -indvars -globaldce -simplifycfg -sink -break-crit-edges -globaldce -gvn -correlated-propagation -bdce -loop-simplifycfg -slp-vectorizer -scalarizer -loop-rotate'

        pass_seq, y_ref = f.reduce_pass(x_best)
        dirname=os.path.expanduser('~/cBench_result')
        file=os.path.join(dirname,f'{args.benchmark}_reduce_best.json')
        data={}
        data[args.benchmark]=[' '.join(pass_seq), y_ref, y_O3]
        with open(file, 'w') as ff:
            json.dump(data, ff, indent=4)
        
    
        
                    
            
        
        
        
        
        
        
   
    
   
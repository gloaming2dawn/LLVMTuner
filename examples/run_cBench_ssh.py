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



parser = argparse.ArgumentParser()
parser.add_argument('--device', required=True, help='')
parser.add_argument('--method', required=True, help='')
parser.add_argument('--benchmark', required=True, help='')
parser.add_argument('--budget', type=int,default=50, help='')
parser.add_argument('--n-parallel', type=int,default=50, help='')
parser.add_argument('--batch-size', type=int, default=1)
args = parser.parse_args()

passes=llvmtuner.searchspace.default_space()
# passes=llvmtuner.searchspace.compilergym_space()
passes.append('')



# 热点在IR不值得优化: security_rijndael_d security_rijndael_e consumer_jpeg_d consumer_tiff2rgba consumer_tiff2bw consumer_tiffdither
# IO噪声大: consumer_jpeg_c

ben2num={'automotive_bitcount':5, 'automotive_qsort1': 10,'automotive_susan_c':50, 'automotive_susan_e':20, 'automotive_susan_s':5,'bzip2d':3,'bzip2e':2,'consumer_jpeg_c':100,'consumer_lame':10, 'consumer_tiffmedian':200,'network_dijkstra':100000,'network_patricia':5000,'office_rsynth':50,'security_blowfish_d':5000, 'security_blowfish_e':5000, 'security_sha':8000, 'telecom_adpcm_c':500,'telecom_adpcm_d':1000, 'telecom_CRC32':50, 'telecom_gsm':20}




ben_dir = os.path.expanduser('~/cBench_V1.1/{}/src_work/'.format(args.benchmark))
cross_flags='--target=aarch64-linux-gnu --sysroot=/home/jiayu/gcc-4.8.5-aarch64/install/aarch64-unknown-linux-gnu/sysroot/ --gcc-toolchain=/home/jiayu/gcc-4.8.5-aarch64/install'
ccmd = f'make ZCC=clangopt LDCC=clangopt CCC_OPTS="{cross_flags}" LD_OPTS="{cross_flags}" -C {ben_dir}'
tmp_dir = os.path.join(os.path.expanduser('~/result_llvmtuner_v5/cBench/'), args.benchmark, args.method)


host="nvidia@TX2-{}.local".format(args.device)
sshC=Connection(host=host)

def run_and_eval_fun():
    run_dir = '/home/nvidia/cBench_V1.1/{}/src_work/'.format(args.benchmark)
    try:
        ret = sshC.put(local=os.path.join(ben_dir,'a.out'), remote=run_dir)
    except Exception as e:
        assert 1==0

    run_cmd = './__run 1 {}'.format(ben2num[args.benchmark])
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



allfiles=[]
files=glob.glob(os.path.join(ben_dir,'*.c'))
for f in files:
    fName = f.split('/')[-1]
    fileroot,fileext=os.path.splitext(fName)
    allfiles.append(fName)

ben2hot={'automotive_bitcount': ['bitcnts.c', 'bitcnt_3.c', 'bitcnt_4.c', 'bitcnt_1.c', 'bitcnt_2.c'], 'automotive_qsort1': ['qsort.c', 'qsort_large.c'], 'automotive_susan_c': ['susan.c'], 'automotive_susan_e': ['susan.c'], 'automotive_susan_s': ['susan.c'], 'bzip2d': ['decompress.c', 'bzlib.c'], 'bzip2e': ['blocksort.c', 'compress.c', 'bzlib.c'], 'consumer_jpeg_c': ['jcphuff.c', 'jccolor.c', 'jfdctint.c', 'jcdctmgr.c', 'jchuff.c', 'jcsample.c', 'jccoefct.c'], 'consumer_lame': ['psymodel.c', 'newmdct.c', 'fft.c', 'takehiro.c', 'quantize-pvt.c', 'quantize.c', 'formatBitstream.c', 'l3bitstream.c', 'util.c', 'lame.c'], 'consumer_tiffmedian': ['tiffmedian.c'], 'network_dijkstra': ['dijkstra_large.c'], 'network_patricia': ['patricia.c', 'patricia_test.c'], 'office_rsynth': ['nsynth.c', 'holmes.c', 'aufile.c'], 'security_blowfish_d': ['bf_enc.c', 'bf_cfb64.c'], 'security_blowfish_e': ['bf_enc.c', 'bf_cfb64.c'], 'security_sha': ['sha.c'], 'telecom_adpcm_c': ['adpcm.c'], 'telecom_adpcm_d': ['adpcm.c'], 'telecom_CRC32': ['crc_32.c'], 'telecom_gsm': ['long_term.c', 'short_term.c', 'lpc.c', 'rpe.c', 'preprocess.c', 'code.c', 'add.c']}

fun_O3 = Function_wrap(ccmd, ben_dir, tmp_dir, run_and_eval_fun, hotfiles=allfiles)
fun_O3.build('-O3')
fun_O3('-O3')
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

    

if args.method == 'O1':
    f.hotfiles =allfiles
    y = f('-O1')
    
if args.method == 'O3':
    f.hotfiles =allfiles
    y = f('-O3')
    # y = f("-mem2reg -div-rem-pairs -jump-threading -loop-unswitch -sroa -indvars -loop-rotate -instcombine -globalopt -tailcallelim -loop-idiom -loop-unroll -function-attrs -loop-deletion")
    # y = f("-mem2reg -div-rem-pairs -jump-threading -loop-unswitch -sroa -indvars -loop-rotate -instcombine -globalopt -tailcallelim -loop-idiom -loop-unroll -functionattrs -loop-deletion")


if args.method=='m-random':
    params_list = []
    for _ in range(args.budget):
        params={}
        for filename in f.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            seq=random.choices(passes, k=len_seq)
            seq=check_seq(seq)
            params[fileroot]=' '.join(seq)
        params_list.append(params)
    
    t0 = time.time()
    with Pool(50) as p:
        flags = p.map(fun.genoptIR, params_list)
    print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
    
    for i in range(len(params_list)):
        if flags[i]:
            y = f(params_list[i])
    
        
        
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
        # y = f(' '.join(seq))
    
    
    
    t0 = time.time()
    with Pool(50) as p:
        flags = p.map(fun.genoptIR, params_list)
    print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
    
    for i in range(len(params_list)):
        y = f(params_list[i])
    
    
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
        
        y=f(' '.join(seq))
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

if args.method=='random_local':
    params_list=[]
    for _ in range(20):
        seq=random.choices(passes, k=len_seq)
        seq=check_seq(seq)
        params={}
        for filename in fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            params[fileroot]=' '.join(seq)
        params_list.append(params)
        # y = f(' '.join(seq))
    
    for i in range(len(params_list)):
        y = f(params_list[i])
    
    
    for i in range(args.budget - 100):
        params=deepcopy(f.best_params)
        filename = random.choice(f.hotfiles)
        fileroot,fileext=os.path.splitext(filename)
        print(fileroot)
        seq=random.choices(passes, k=len_seq)
        params[fileroot]=' '.join(seq)
        y = f(params)
        

if args.method=='random-dataset':
    pass
    
if args.method=='BO-dataset':
    pass


if args.method=='test-gp': 
    import torch

    if not os.path.isfile( os.path.join(tmp_dir,'cfg_json_list.json') ):
        params_list=[]
        for _ in range(args.budget):
            seq=random.choices(passes, k=len_seq)
            seq=check_seq(seq)
            params={}
            for filename in fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                params[fileroot]=' '.join(seq)
            params_list.append(params)
            # y = f(' '.join(seq))
        
        
        
        t0 = time.time()
        with Pool(50) as p:
            flags = p.map(fun.genoptIR, params_list)
        print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        
        cfg_json_list=[]
        for params in params_list:
            cfg={}
            cfg['tmp_dir']=tmp_dir
            cfg['params']=params
            cfg_json=json.dumps(cfg)
            cfg_json_list.append(cfg_json)
            
        with open(os.path.join(tmp_dir, 'cfg_json_list.json'),'w') as ff:
            json.dump(cfg_json_list, ff, indent=4)
        
        
    with open(os.path.join(tmp_dir, 'cfg_json_list.json'),'r') as ff:
        cfg_json_list=json.load(ff)
    
    # for cfg_json in cfg_json_list:
    #     cfg = json.loads(cfg_json)
    #     y = fun(cfg['params'])
    
    with open(os.path.join(tmp_dir, 'result.json'),'r') as ff:
        result_list=ff.readlines()
        cfg_path_list=[]
        y_list=[]
        for d in result_list:
            a=json.loads(d)
            cfg_path_list.append(a[0])
            y_list.append(a[1])
        
        

    
    stats_list = read_optstats_from_cfgpathlist(cfg_path_list)
    # stats_list = read_optstats_from_cfgjsonlist(cfg_json_list)
    all_X, feature_names,vector_initial = stats2vec(stats_list)
    # p_list=list(zip(feature_names, all_X[1], vector_initial[1]))
    # for x in p_list:
    #     print(x)
        
    BO=BO(
        fun=fun,
        passes=passes, 
        len_seq=len_seq,
        budget=args.budget, 
        acqf='EI',
        beta=4,
        n_parallel=args.n_parallel,
        )
    
    n_initial = 100
    indices = np.random.choice(all_X.shape[0], n_initial, replace=False)
    indices = np.array(range(100,200))
    indices_others = np.setdiff1d(np.arange(all_X.shape[0]),indices)
    X = list(all_X[indices])
    fX = list(np.array(y_list)[indices])
    cand_X = list(all_X[indices_others])
    cand_Y = list(np.array(y_list)[indices_others])
    print("{}) fbest = {:.4f} f_current = {:.4f}".format(len(fX), np.min(fX), fX[-1]))
    for iii in range(500):
        model, _ = BO.train_gp(X,fX)
        acq_values = BO.predict(model, cand_X)
        index = acq_values.index(max(acq_values))
        X_next = cand_X[index]
        
        posterior = model.posterior(torch.tensor(X_next).unsqueeze(0))
        mean = posterior.mean
        variance = posterior.variance
        print('next mean',mean, 'next variance', variance, 'next acqf', acq_values[index])
        
        
        fX_next = cand_Y[index]
        X = np.vstack((X, deepcopy(X_next)))
        fX.append(deepcopy(fX_next))
        
        x_mean = np.mean(X, axis=0)
        fname_list=[]
        for i in range(len(x_mean)):
            if x_mean[i]==0:
                fname_list.append(feature_names[i])
                # print(feature_names[i])
                
                for xx in cand_X:
                    if xx[i]!=0:
                        posterior = model.posterior(torch.tensor(xx).unsqueeze(0))
                        mean = posterior.mean
                        variance = posterior.variance
                        print('mean',mean, 'variance', variance)
                    
                        
                        
                
        print(fname_list, len(fname_list))
        print("{}) fbest = {:.4f} f_current = {:.4f}".format(len(fX), np.min(fX), fX[-1]))
        cand_X.pop(index)
        cand_Y.pop(index)
        
        
        
        
    
    # X = all_X[100:200]
    # fX = y_list[100:200]
    # model, _ = BO.train_gp(X,fX)
    # aaa= list(zip(feature_names, model.covar_module.base_kernel.lengthscale.cpu().squeeze()))
    # x_mean = np.mean(X, axis=0)
    # for i in range(len(x_mean)):
    #     if x_mean[i]==0:
    #         print(feature_names[i])
    # for x in aaa:
    #     print(x)
    
    
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
    
if args.method == 'test-m':
    y_O3 = f('-O3')
    dirname=os.path.expanduser('~/cBench_result')
    file=os.path.join(dirname,f'{args.benchmark}_reduce_best.json')
    with open(file,'r') as ff:
        data=json.load(ff)
    x_best, y_best, _=data[args.benchmark]
    print(args.benchmark, y_best, y_O3, y_O3/y_best)
    
    params_initial = {}
    for filename in f.hotfiles:
        fileroot,fileext=os.path.splitext(filename)
        params_initial[fileroot]=x_best
    
                
        
    
    data={}
    data['O3'] = y_O3
    data['all'] = f(params_initial)
    
    for filename in f.hotfiles:
        params = deepcopy(params_initial)
        fileroot,fileext=os.path.splitext(filename)
        params[fileroot]='-O3'
        data[fileroot] = f(params)
        
            
        
    print(data)
    
    
    
    
if args.method == 'test':
    f = Function_wrap(ccmd, tmp_dir, run_and_eval_fun, hotfiles, repeat = 3, adaptive_measure = False)
    y_O3 = f('-O3')
    
    dirname=os.path.expanduser('~/cBench_result')
    file=os.path.join(dirname,'best.json')
    
    with open(file,'r') as ff:
        data=json.load(ff)
        x_best_record, y_best_record, y_O3_record=data[args.benchmark]
    print(args.benchmark, y_best_record)

    
    
    dirname=os.path.expanduser('~/cBench_result')
    file=os.path.join(dirname,f'{args.benchmark}_reduce_best.json')
    with open(file,'r') as ff:
        data=json.load(ff)
    x_best, y_best, y_O3=data[args.benchmark]
    print('after reduce: ',args.benchmark, x_best, y_best, y_O3, y_O3/y_best)
    
    # if args.benchmark == 'consumer_jpeg_c':
    #     x_best_record = 
    
    y1 = f(x_best_record)
    y2 = f(x_best)
    

    print(y1,y2)
    
   
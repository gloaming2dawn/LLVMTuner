# -*- coding: utf-8 -*-
"""
Created on Wed Mar  2 17:54:48 2022

@author: scjzhadmin
"""
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
from llvmtuner.function_wrap import Function_wrap
from llvmtuner.gen_hotfiles import find_hot_files


parser = argparse.ArgumentParser()
parser.add_argument('--method', required=True, help='')
parser.add_argument('--benchmark', required=True, help='')
parser.add_argument('--budget', type=int,default=50, help='')
parser.add_argument('--n-parallel', type=int,default=50, help='')
parser.add_argument('--batch-size', type=int, default=1)
args = parser.parse_args()

passes=llvmtuner.searchspace.default_space()

ben_dir = os.path.expanduser('~/cBench_V1.1/{}/src_work/'.format(args.benchmark))
run_dir = ben_dir
ccmd = 'make ZCC=clangopt LDCC=clangopt -C {}'.format(ben_dir)
tmp_dir = os.path.join(os.path.expanduser('~/local_result_llvmtuner/cBench/'), args.benchmark, args.method)


# 热点在IR不值得优化: security_rijndael_d security_rijndael_e consumer_jpeg_d consumer_tiff2rgba consumer_tiff2bw consumer_tiffdither
# IO噪声大: consumer_jpeg_c
ben2num={'automotive_bitcount':15, 'automotive_qsort1': 30,'automotive_susan_c':100, 'automotive_susan_e':50, 'automotive_susan_s':10,'bzip2d':10,'bzip2e':5,'consumer_jpeg_c':250,'consumer_lame':20, 'consumer_tiffmedian':400,'network_dijkstra':200000,'network_patricia':10000,'office_rsynth':200,'security_blowfish_d':20000, 'security_blowfish_e':20000, 'security_sha':25000, 'telecom_adpcm_c':1000,'telecom_adpcm_d':2000, 'telecom_CRC32':200, 'telecom_gsm':100}

ben2hot={'automotive_bitcount': ['bitcnts.c', 'bitcnt_3.c', 'bitcnt_4.c', 'bitcnt_1.c', 'bitcnt_2.c'], 'automotive_qsort1': ['qsort.c', 'qsort_large.c'], 'automotive_susan_c': ['susan.c'], 'automotive_susan_e': ['susan.c'], 'automotive_susan_s': ['susan.c'], 'bzip2d': ['decompress.c', 'bzlib.c'], 'bzip2e': ['blocksort.c', 'compress.c', 'bzlib.c'], 'consumer_jpeg_c': ['jcphuff.c', 'jccolor.c', 'jfdctint.c', 'jcdctmgr.c', 'jchuff.c', 'jcsample.c', 'jccoefct.c'], 'consumer_lame': ['psymodel.c', 'newmdct.c', 'fft.c', 'takehiro.c', 'quantize-pvt.c', 'quantize.c', 'formatBitstream.c', 'l3bitstream.c', 'util.c', 'lame.c'], 'consumer_tiffmedian': ['tiffmedian.c'], 'network_dijkstra': ['dijkstra_large.c'], 'network_patricia': ['patricia.c', 'patricia_test.c'], 'office_rsynth': ['nsynth.c', 'holmes.c', 'aufile.c'], 'security_blowfish_d': ['bf_enc.c', 'bf_cfb64.c'], 'security_blowfish_e': ['bf_enc.c', 'bf_cfb64.c'], 'security_sha': ['sha.c'], 'telecom_adpcm_c': ['adpcm.c'], 'telecom_adpcm_d': ['adpcm.c'], 'telecom_CRC32': ['crc_32.c'], 'telecom_gsm': ['long_term.c', 'short_term.c', 'lpc.c', 'rpe.c', 'preprocess.c', 'code.c', 'add.c']}



hotfiles=ben2hot[args.benchmark]






def run_and_eval_fun():
    run_cmd = './__run 1 {}'.format(ben2num[args.benchmark])
    cwd = ben_dir
    ret = subprocess.run(run_cmd, shell=True, cwd=cwd, capture_output=True)
    if ret.returncode != 0:
        return inf
    else:
        temp=ret.stderr.decode('utf-8').strip()
        real=temp.split('\n')[-3]
        searchObj = re.search( r'real\s*(.*)m(.*)s.*', real)
        runtime = int(searchObj[1])*60+float(searchObj[2])
        
        # user=temp.split('\n')[-2]
        # searchObj = re.search( r'user\s*(.*)m(.*)s.*', user)
        # usertime = int(searchObj[1])*60+float(searchObj[2])
        
        # syst=temp.split('\n')[-1]
        # searchObj = re.search( r'sys\s*(.*)m(.*)s.*', syst)
        # systime = int(searchObj[1])*60+float(searchObj[2])
        
        # print(runtime, usertime, systime, runtime/(usertime+systime))
        
        return runtime 

def gen_profdata():
        cmd = 'export LLVM_PROFILE_FILE="default%p.profraw"'
        ret = subprocess.run(cmd, shell=True, capture_output=True)
        assert ret.returncode == 0

        y = run_and_eval_fun()
        assert y != inf

        cmd = 'llvm-profdata merge *.profraw -o default.profdata'
        ret = subprocess.run(cmd, shell=True, capture_output=True, cwd =run_dir)
        assert ret.returncode == 0

        cmd = 'rm *.profraw'
        ret = subprocess.run(cmd, shell=True, capture_output=True, cwd =run_dir)
        assert ret.returncode == 0
        
        profdata=os.path.join(run_dir, 'default.profdata')
        return profdata




pgo_dir = os.path.join(ben_dir,'tmp')
fun_genprofdata = Function_wrap(ccmd, ben_dir, pgo_dir, run_and_eval_fun, is_genprofdata=True)
fun_genprofdata.gen_profdata = gen_profdata
profdata = fun_genprofdata('-O3')
print('profdata:', profdata)
hot_files = find_hot_files(pgo_dir, profdata)
with open(ben_dir+'/hotfiles.json', 'w') as f:
    json.dump(hot_files, f, indent=4)

assert 1==0


allfiles=[]
files=glob.glob(os.path.join(ben_dir,'*.c'))
for f in files:
    fName = f.split('/')[-1]
    fileroot,fileext=os.path.splitext(fName)
    allfiles.append(fName)

f_O3 = Function_wrap(ccmd, ben_dir, tmp_dir, run_and_eval_fun, hotfiles=allfiles)
f_O3.build('-O3')
# y_O3 = f_O3('-O3')

f = Function_wrap(ccmd, ben_dir, tmp_dir, run_and_eval_fun, hotfiles)





len_seq=150
# def check_seq(seq):
#     cgprofile_count = seq.count('-cg-profile')
#     if cgprofile_count>1:
#         for _ in range(cgprofile_count-1):
#             seq.remove('-cg-profile')
#             seq.append('-inline')
#     return seq

def check_seq(seq):
    cgprofile_count = seq.count('-cg-profile')
    if cgprofile_count>1:
        for _ in range(cgprofile_count-1):
            index = seq.index('-cg-profile')
            seq[index] = ''
            # seq.remove('-cg-profile')
            # seq.append('-inline')
    return seq


if args.method == 'O3':
    f = Function_wrap(cmd, tmp_dir, run_and_eval_fun, max_n_measure=100,adaptive_measure = False)
    y = f('-O3')
    y = f("-mem2reg -div-rem-pairs -jump-threading -loop-unswitch -sroa -indvars -loop-rotate -instcombine -globalopt -tailcallelim -loop-idiom -loop-unroll -function-attrs -loop-deletion")


if args.method=='random': 
    import random as random
    seqs = []
    for _ in range(args.budget):
        seq=random.choices(passes, k=len_seq)
        seq=check_seq(seq)
        seqs.append(' '.join(seq))
        # y = f(' '.join(seq))
        # seqs.append(' '.join(seq))
    
    def genoptIR(s):
        return f.gen_optIR(s)
    
    t0 = time.time()
    with Pool(50) as p:
        flags = p.map(genoptIR, seqs)
    print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
    
    for i in range(len(seqs)):
        if flags[i]:
            y = f(seqs[i])
    
    
    
if args.method=='ngopt':
    import nevergrad as ng
    params = ng.p.Choice(
            choices=passes,
            repetitions=len_seq,
            deterministic=True
        )
    optimizer=ng.optimizers.NGOpt(parametrization=params, budget=args.budget, num_workers=1)
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
        fun=f,
        passes=passes, 
        len_seq=len_seq,
        budget=args.budget, 
        acqf='EI',# or UCB
        beta=1.96,
        n_parallel=args.n_parallel,
        n_init=20,
        )

    BO.minimize()
        
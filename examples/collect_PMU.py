# -*- coding: utf-8 -*-
"""
Created on Wed Mar  2 17:54:48 2022

@author: scjzhadmin
"""
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

# python collect_PMU.py --device=6 --benchmark=security_sha 
# python collect_PMU.py --device=6 --benchmark=consumer_lame
# python collect_PMU.py --device=6 --benchmark=network_dijkstra


parser = argparse.ArgumentParser()
parser.add_argument('--device', required=True, help='')
parser.add_argument('--method', default='pmu', help='')
parser.add_argument('--optlevel', default='O3', help='')
parser.add_argument('--benchmark', required=True, help='')
parser.add_argument('--budget', type=int,default=50, help='')
parser.add_argument('--n-parallel', type=int,default=50, help='')
parser.add_argument('--batch-size', type=int, default=1)
parser.add_argument('--server', default='cpu')
args = parser.parse_args()

passes, passes_clear, pass2kind, O3_trans_seq=default_space()



# network_dijkstra噪声太大，network_patricia噪声在3%
ben2cmd = {'automotive_bitcount': './__run 1 5', 'automotive_qsort1': './__run 1 10' ,'automotive_susan_c':'./__run 9 5', 'automotive_susan_e':'./__run 9 2', 'automotive_susan_s':'./__run 19 1','bzip2d':'./__run 12 1','bzip2e':'./__run 12 1','consumer_jpeg_c':'./__run 15 2','consumer_lame':'./__run 6 1', 'consumer_tiffmedian':'./__run 11 1','network_dijkstra':'./__run 10 1','network_patricia':'./__run 13 20','security_blowfish_d':'./__run 20 20', 'security_blowfish_e':'./__run 20 20', 'security_sha':'./__run 4 10', 'telecom_adpcm_c':'./__run 2 3','telecom_adpcm_d':'./__run 2 5', 'telecom_CRC32':'./__run 2 1', 'telecom_gsm':'./__run 6 1', 'consumer_jpeg_d':'./__run 3 1', 'consumer_tiff2bw':'./__run 3 1', 'consumer_tiff2rgba':'./__run 3 1', 'office_stringsearch1': './__run 4 50', 'consumer_tiffdither': './__run 3 1', 'security_rijndael_d':'./__run 4 1', 'security_rijndael_e':'./__run 4 1'}


ben2hot={'automotive_bitcount': ['bitcnts', 'bitcnt_4', 'bitcnt_3', 'bitcnt_2'], 'automotive_qsort1': ['qsort', 'qsort_large'], 'automotive_susan_c': ['susan'], 'automotive_susan_e': ['susan'], 'automotive_susan_s': ['susan'], 'bzip2d': ['bzlib', 'decompress'], 'bzip2e': ['blocksort', 'compress', 'bzlib'], 'consumer_jpeg_c': ['jcphuff', 'jcdctmgr', 'jfdctint', 'jccolor', 'jchuff', 'jccoefct'], 'consumer_jpeg_d': ['jidctint', 'jdhuff', 'jdcolor', 'jdsample'], 'consumer_lame': ['psymodel', 'newmdct', 'fft', 'quantize', 'takehiro','quantize-pvt', 'l3bitstream', 'formatBitstream'], 'consumer_tiff2bw': ['tif_lzw', 'tif_predict', 'tiff2bw'], 'consumer_tiff2rgba': ['tif_lzw', 'tif_getimage', 'tif_predict'], 'consumer_tiffmedian': ['tiffmedian'], 'network_dijkstra': ['dijkstra_large'], 'network_patricia': ['patricia'], 'office_stringsearch1': ['pbmsrch_large'], 'security_blowfish_d': ['bf_enc', 'bf_cfb64'], 'security_blowfish_e': ['bf_enc', 'bf_cfb64'], 'security_sha': ['sha'], 'telecom_CRC32': ['crc_32'], 'telecom_adpcm_c': ['adpcm'], 'telecom_adpcm_d': ['adpcm'], 'telecom_gsm': ['long_term', 'short_term', 'preprocess', 'rpe', 'lpc'], 'consumer_tiffdither':['tif_fax3','tiffdither','tif_lzw'], 'security_rijndael_d':['aes'], 'security_rijndael_e':['aes']}

#consumer_lame, consumer_tiff2bw

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

tmp_dir = os.path.join(os.path.expanduser('~/result_llvmtuner_17/cBench/'), args.benchmark, args.method)
binary_name = 'a.out'

host="nvidia@TX2-{}.local".format(args.device)
sshC=Connection(host=host)

run_dir = '/home/nvidia/cBench_V1.1/{}/src_work/'.format(args.benchmark)
run_cmd = ben2cmd[args.benchmark]

def run_and_eval_fun():
    try:
        ret = sshC.put(local=os.path.join(ben_dir,'a.out'), remote=run_dir)
    except Exception as e:
        try:
            time.sleep(3)
            ret = sshC.put(local=os.path.join(ben_dir,'a.out'), remote=run_dir)
        except Exception as e:
            try:
                time.sleep(3)
                ret = sshC.put(local=os.path.join(ben_dir,'a.out'), remote=run_dir)
            except Exception as e:
                assert 1==0, [os.path.join(ben_dir,'a.out'), run_dir]

    try:
        timeout_seconds = 20
        with sshC.cd(run_dir):
            ret=sshC.run(f'timeout {timeout_seconds} {run_cmd}' , hide=True, timeout=timeout_seconds) 
            # some benchmarks have bug, we need to clear the output, otherwise the next run will cost much more time
            if args.benchmark == 'consumer_tiff2rgba':
                sshC.run(f'rm output_largergba.tif' , hide=True, timeout=timeout_seconds)
            if args.benchmark == 'consumer_jpeg_d':
                sshC.run(f'rm output_large_decode.ppm' , hide=True, timeout=timeout_seconds)
            if args.benchmark == 'consumer_tiffmedian':
                sshC.run(f'rm output_largemedian.tif' , hide=True, timeout=timeout_seconds)
            if args.benchmark == 'security_rijndael_d':
                sshC.run(f'rm output_large.dec' , hide=True, timeout=timeout_seconds)
            if args.benchmark == 'security_rijndael_e':
                sshC.run(f'rm output_large.enc' , hide=True, timeout=timeout_seconds)
                
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

def collect_pmu():
    try:
        ret = sshC.put(local=os.path.join(ben_dir,'a.out'), remote=run_dir)
    except Exception as e:
        try:
            time.sleep(3)
            ret = sshC.put(local=os.path.join(ben_dir,'a.out'), remote=run_dir)
        except Exception as e:
            try:
                time.sleep(3)
                ret = sshC.put(local=os.path.join(ben_dir,'a.out'), remote=run_dir)
            except Exception as e:
                assert 1==0, [os.path.join(ben_dir,'a.out'), run_dir]

    try:
        timeout_seconds = 20
        with sshC.cd(run_dir):
            perf_cmd = 'perf stat -e branch-misses,cache-misses,cache-references,cpu-cycles,instructions,cpu-clock,L1-dcache-load-misses,L1-dcache-loads,L1-dcache-store-misses,L1-dcache-stores,branch-load-misses,branch-loads'
            ret=sshC.run(f'timeout {timeout_seconds} {perf_cmd} {run_cmd}' , hide=False, timeout=timeout_seconds) 
            # some benchmarks have bug, we need to clear the output, otherwise the next run will cost much more time
            if args.benchmark == 'consumer_tiff2rgba':
                sshC.run(f'rm output_largergba.tif' , hide=True, timeout=timeout_seconds)
            if args.benchmark == 'consumer_jpeg_d':
                sshC.run(f'rm output_large_decode.ppm' , hide=True, timeout=timeout_seconds)
            if args.benchmark == 'consumer_tiffmedian':
                sshC.run(f'rm output_largemedian.tif' , hide=True, timeout=timeout_seconds)
            if args.benchmark == 'security_rijndael_d':
                sshC.run(f'rm output_large.dec' , hide=True, timeout=timeout_seconds)
            if args.benchmark == 'security_rijndael_e':
                sshC.run(f'rm output_large.enc' , hide=True, timeout=timeout_seconds)
    
    
    except invoke.exceptions.UnexpectedExit:
        assert 1==0
    except invoke.exceptions.CommandTimedOut:
        assert 1==0


     

allfiles=[]
files=glob.glob(os.path.join(ben_dir,'*.c'))
for f in files:
    fName = f.split('/')[-1]
    fileroot,fileext=os.path.splitext(fName)
    allfiles.append(fName)
allfiles=sorted(allfiles)



fun_O3 = Function_wrap(ccmd_g, ben_dir, tmp_dir, run_and_eval_fun, hotfiles=allfiles)
fun_O3.repeat = 10
fun_O3.adaptive_measure = False
t0=time.time()
print('-----------------build -O3-----------------')
fun_O3.build(f'default<O3>')
print('O3 compilation time:',time.time()-t0)

hotfiles=ben2hot[args.benchmark]
hotfiles = hotfiles[:1]
fun = Function_wrap(ccmd, ben_dir, tmp_dir, collect_pmu, hotfiles)
fun.build(f'default<{args.optlevel}>')



if __name__ == "__main__":
    if args.method == 'pmu':
        collect_pmu()

    
    


    

        
    
        
                    
            
        
        
        
        
        
        
   
    
   
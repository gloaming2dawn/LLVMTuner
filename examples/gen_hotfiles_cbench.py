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
args = parser.parse_args()

passes=llvmtuner.searchspace.default_space()
passes.append('')

host="nvidia@TX2-{}.local".format(args.device)
sshC=Connection(host=host)

with open(os.path.join(os.path.expanduser('~/cBench_V1.1/'),'cBench_name.txt')) as file:
    benchmarks = [line.strip() for line in file]
print(benchmarks)
# 热点在IO不值得优化: security_rijndael_d security_rijndael_e consumer_jpeg_d consumer_tiff2rgba consumer_tiff2bw consumer_tiffdither
# IO噪声大: consumer_jpeg_c

ben2num={'automotive_bitcount':5, 'automotive_qsort1': 10,'automotive_susan_c':50, 'automotive_susan_e':20, 'automotive_susan_s':5,'bzip2d':3,'bzip2e':2,'consumer_jpeg_c':100,'consumer_lame':10, 'consumer_tiffmedian':200,'network_dijkstra':100000,'network_patricia':5000,'security_blowfish_d':5000, 'security_blowfish_e':5000, 'security_sha':8000, 'telecom_adpcm_c':500,'telecom_adpcm_d':1000, 'telecom_CRC32':50, 'telecom_gsm':20, 'consumer_jpeg_d':30, 'consumer_tiff2bw':100, 'consumer_tiff2rgba':30, 'office_stringsearch1': 100000} 
ben2num={'consumer_jpeg_d':30, 'consumer_tiff2bw':100, 'consumer_tiff2rgba':30, 'office_stringsearch1': 100000} 

# ben2num={'security_blowfish_d':5000, 'security_blowfish_e':5000, 'security_sha':8000, 'telecom_adpcm_c':500,'telecom_adpcm_d':1000, 'telecom_CRC32':50, 'telecom_gsm':20}

#compilation failed in LLVM 16: 'office_rsynth':50, consumer_mad, office_ghostscript, office_ispell, security_pgp_d,security_pgp_e
#运行错误security_rijndael_d, security_rijndael_e
# 热点在IO不值得优化: consumer_tiffdither,
bad_benchmarks = ['office_rsynth', 'consumer_mad','consumer_tiffdither', 'office_ghostscript', 'office_ispell','security_pgp_d','security_pgp_e','security_rijndael_d', 'security_rijndael_e']

ben2hot={}
for benchmark in ben2num:
# for benchmark in benchmarks:
    if benchmark in bad_benchmarks:
        continue

    print(f'-----------------{benchmark}-----------------')
    ben_dir = os.path.expanduser('~/cBench_V1.1/{}/src_work/'.format(benchmark))
    cross_flags='--target=aarch64-linux-gnu --sysroot=/home/jiayu/gcc-4.8.5-aarch64/install/aarch64-unknown-linux-gnu/sysroot/ --gcc-toolchain=/home/jiayu/gcc-4.8.5-aarch64/install'
    ccmd = f'make ZCC=clangopt LDCC=clangopt CCC_OPTS="{cross_flags}" LD_OPTS="{cross_flags}" -C {ben_dir}'
    ccmd_g = f'make ZCC=clangopt LDCC=clangopt CCC_OPTS="{cross_flags} -g" LD_OPTS="{cross_flags} -g" -C {ben_dir}'

    tmp_dir = os.path.join(os.path.expanduser('~/result_llvmtuner_v5/cBench/'), benchmark, 'O3')
    binary_name = 'a.out'
    

    run_dir = '/home/nvidia/cBench_V1.1/{}/src_work/'.format(benchmark)
    num=ben2num[benchmark]
    run_cmd = f'./__run 1 {num}'

    def run_and_eval_fun():
        try:
            ret = sshC.put(local=os.path.join(ben_dir,'a.out'), remote=run_dir)
        except Exception as e:
            assert 1==0

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


    fun_O3 = Function_wrap(ccmd_g, ben_dir, tmp_dir, run_and_eval_fun, hotfiles=allfiles, repeat = 1, adaptive_measure = False)
    print('-----------------build -O3-----------------')
    fun_O3.build('-O3')
    fun_O3('-O3')

    module2funcnames = fun_O3._get_func_names()
    folded_perf_result = perf_record(sshC, ben_dir, run_dir, run_cmd)
    hotfiles = gen_hotfiles(module2funcnames, binary_name, folded_perf_result)
    print(hotfiles)
    ben2hot[benchmark]=hotfiles

print(ben2hot)


    

    

   
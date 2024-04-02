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
from llvmtuner.searchspace import default_space, passlist2str, parse_O3string
from llvmtuner.feature_extraction import read_optstats_from_cfgpathlist,read_optstats_from_cfgjsonlist,stats2vec
from llvmtuner.BO.BO import BO
from llvmtuner.function_wrap import Function_wrap
from llvmtuner.gen_hotfiles import perf_record, gen_hotfiles

# python run_cBench_ssh.py --device=1 --method=O3 --benchmark=automotive_bitcount --budget=50

parser = argparse.ArgumentParser()
parser.add_argument('--device', required=True, help='')
parser.add_argument('--method', required=True, help='')
parser.add_argument('--budget', type=int,default=50, help='')
parser.add_argument('--n-parallel', type=int,default=50, help='')
parser.add_argument('--batch-size', type=int, default=1)
args = parser.parse_args()

passes, pass2kind, O3_trans_seq=default_space()
# passes=llvmtuner.searchspace.compilergym_space()
# passes.append('')



# 热点在IR不值得优化: security_rijndael_d security_rijndael_e consumer_jpeg_d consumer_tiff2rgba consumer_tiff2bw consumer_tiffdither
# IO噪声大: consumer_jpeg_c

ben2num={'automotive_bitcount':5, 'automotive_qsort1': 10,'automotive_susan_c':50, 'automotive_susan_e':20, 'automotive_susan_s':5,'bzip2d':3,'bzip2e':2,'consumer_jpeg_c':100,'consumer_lame':10, 'consumer_tiffmedian':200,'network_dijkstra':100000,'network_patricia':5000,'security_blowfish_d':5000, 'security_blowfish_e':5000, 'security_sha':8000, 'telecom_adpcm_c':500,'telecom_adpcm_d':1000, 'telecom_CRC32':50, 'telecom_gsm':40, 'consumer_jpeg_d':100, 'consumer_tiff2bw':100, 'consumer_tiff2rgba':60, 'office_stringsearch1': 100000} 

bad_ben=[]
with open('/home/jiayu/cBench_V1.1/cBench_name.txt','r') as file:
    for name in file:
        if name.strip() not in ben2num:
            bad_ben.append(name.strip())
            print(name.strip())

bad_ben=['consumer_tiffdither', 'security_rijndael_d', 'security_rijndael_e']

for ben in bad_ben:
    ben_dir = os.path.expanduser('~/cBench_V1.1/{}/src_work/'.format(ben))
    cross_flags='--target=aarch64-linux-gnu --sysroot=/home/jiayu/gcc-4.8.5-aarch64/install/aarch64-unknown-linux-gnu/sysroot/ --gcc-toolchain=/home/jiayu/gcc-4.8.5-aarch64/install'
    ccmd = f'make ZCC=clangopt LDCC=clangopt CCC_OPTS="{cross_flags}" LD_OPTS="{cross_flags}" -C {ben_dir}'
    ccmd_g = f'make ZCC=clangopt LDCC=clangopt CCC_OPTS="{cross_flags} -g" LD_OPTS="{cross_flags} -g" -C {ben_dir}'

    tmp_dir = os.path.join(os.path.expanduser('~/tmp/cBench/'), ben, args.method)
    binary_name = 'a.out'

    host="nvidia@TX2-{}.local".format(args.device)
    sshC=Connection(host=host)

    run_dir = '/home/nvidia/cBench_V1.1/{}/src_work/'.format(ben)
    run_cmd = './__run 1'




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
    fun_O3.repeat = 10
    fun_O3.adaptive_measure = False
    t0=time.time()
    print('-----------------build -O3-----------------')
    flag = fun_O3.build('default<O3>')
    if flag:
        print('O3 compilation time:',time.time()-t0)
        print(ben)
        y = fun_O3('default<O3>')
        print(y)


        
    
        
                    
            
        
        
        
        
        
        
   
    
   
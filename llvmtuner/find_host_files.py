# -*- coding: utf-8 -*-
"""
Created on Thu Dec 29 23:09:54 2022

@author: jiayu
"""

import numpy as np
import time
import subprocess
import os
import hashlib
import json
from multiprocessing import Pool
import llvmtuner
from llvmtuner import searchspace
#from llvmtuner.feature_extraction import feature_extraction
passes=llvmtuner.searchspace.default_space()

ben2num={'automotive_bitcount':5, 'automotive_qsort1': 10,'automotive_susan_c':50, 'automotive_susan_e':20, 'automotive_susan_s':5,'bzip2d':3,'bzip2e':2,'consumer_jpeg_c':100,'consumer_lame':10, 'consumer_tiffmedian':200,'network_dijkstra':100000,'network_patricia':5000,'office_rsynth':50,'security_blowfish_d':5000, 'security_blowfish_e':5000, 'security_sha':8000, 'telecom_adpcm_c':500,'telecom_adpcm_d':1000, 'telecom_CRC32':50, 'telecom_gsm':20}


def find_host_files(benchmark):
    ben_dir = os.path.expanduser('~/cBench_V1.1/{}/src_work/'.format(benchmark))
    par_dir=os.path.expanduser('~/result_llvmtuner/cBench/{}/random/samples/'.format(benchmark))
    subdirs = os.listdir(par_dir)
    files = os.listdir(ben_dir)
    files = [x  for x in files if x.endswith('.c')]
    counts = []
    host_files = []
    for file in files:
        fileroot, fileext= os.path.splitext(file)
        IR_pgouse=os.path.join(par_dir, ben_dir, fileroot +'.pgouse.bc')
        ir2dictpass='/home/jiayu/LLVMTuner_v3/ir2count/build/lib/libir2count.so'
        cmd=f'opt -load-pass-plugin {ir2dictpass} -passes=ir2dict -disable-output {IR_pgouse}'
        ret = subprocess.run(cmd, shell=True, capture_output=True)
        assert ret.returncode == 0, cmd
        count = int(ret.stdout.decode('utf-8').strip())
        print(file, count)
        counts.append(count)
    ratios = np.array(counts)/np.sum(counts)
    b=np.sort(ratios)[::-1]
    ind = np.argsort(ratios)[::-1]
    files=np.array(files)[ind]
    
    cumratios=np.cumsum(b)
    a = files[cumratios<0.99]
    host_files = files[:len(a)+1]
    print(b[:len(a)+1])
    print(cumratios[:len(a)+1])
    print(host_files)
    return list(host_files)
    
ben2hot={}
for benchmark in ben2num:
    print('='*20,benchmark)
    host_files=find_host_files(benchmark)
    ben2hot[benchmark]=host_files
print(ben2hot)
    # IR = os.path.join(directory, subdir, 'adpcm.opt.bc')
    # ir2dictpass='/home/jiayu/LLVMTuner_v3/ir2count/build/lib/libiir2count.so'
    # cmd=f'opt -load-pass-plugin {ir2dictpass} -passes=ir2dict -disable-output {IR} 2> {subdir+".txt"}'
    # subprocess.run(cmd, shell=True)
    
#     with open(subdir+".txt", 'rb') as f:
#         data=f.read()
#         md5sum = hashlib.md5(data).hexdigest()
#         if md5sum not in md5sums:
#             print(data)
#             md5sums.add(md5sum)
# -*- coding: utf-8 -*-
"""
Created on Wed Dec  7 01:03:57 2022

@author: jiayu
"""

import argparse
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('--device', required=True, help='')#1,2,3, 5,6
parser.add_argument('--budget', type=int,default=1010, help='')
parser.add_argument('--n-parallel', type=int,default=50, help='')
parser.add_argument('--batch-size', type=int, default=1)
args = parser.parse_args()

all_benchmarks = ['automotive_bitcount', 'automotive_qsort1', 'automotive_susan_c', 'automotive_susan_e', 'automotive_susan_s', 'bzip2d', 'bzip2e', 'consumer_jpeg_c', 'consumer_jpeg_d', 'consumer_lame', 'consumer_tiff2bw', 'consumer_tiff2rgba', 'consumer_tiffdither', 'consumer_tiffmedian', 'network_dijkstra', 'network_patricia', 'office_stringsearch1', 'security_blowfish_d', 'security_blowfish_e', 'security_rijndael_d', 'security_rijndael_e', 'security_sha', 'telecom_CRC32', 'telecom_adpcm_c', 'telecom_adpcm_d', 'telecom_gsm']

final_benchmarks = ['automotive_bitcount', 'automotive_qsort1', 'bzip2d', 'bzip2e', 'consumer_jpeg_c', 'consumer_jpeg_d', 'consumer_lame', 'consumer_tiff2bw', 'consumer_tiff2rgba', 'security_blowfish_d', 'security_blowfish_e', 'security_sha','telecom_gsm','consumer_tiffdither']

final_benchmarks =['automotive_bitcount', 'automotive_qsort1', 'bzip2d', 'bzip2e', 'consumer_jpeg_c', 'consumer_jpeg_d', 'consumer_lame', 'consumer_tiff2bw', 'consumer_tiff2rgba', 'consumer_tiffdither', 'security_blowfish_d', 'security_blowfish_e', 'security_sha', 'telecom_gsm']

if args.device == '1':
    bens=['automotive_bitcount', 'automotive_qsort1', 'bzip2d']#
    bens = ['automotive_bitcount', 'automotive_qsort1', 'automotive_susan_c', 'automotive_susan_e', 'automotive_susan_s']
    server='cpu'
    # bens=['automotive_susan_e']

if args.device == '3':
    bens=['bzip2e', 'consumer_jpeg_c', 'consumer_jpeg_d']
    bens = ['bzip2d', 'bzip2e', 'consumer_jpeg_c', 'consumer_jpeg_d', 'consumer_lame']
    server = 'cuda' 
    cuda_number = 1

# if args.device == '3':
#     bens=['consumer_lame', 'consumer_tiffmedian','network_dijkstra','network_patricia']
#     # bens=['consumer_lame', 'consumer_tiffmedian']

if args.device == '4':
    bens=['consumer_lame','consumer_tiff2bw','consumer_tiffdither']#'consumer_tiff2bw',
    bens=['consumer_tiff2bw', 'consumer_tiff2rgba', 'consumer_tiffdither', 'consumer_tiffmedian', 'network_patricia']
    server = 'cuda' 
    cuda_number = 0

if args.device == '5':
    bens=['consumer_tiff2rgba', 'security_blowfish_d']
    bens=['office_stringsearch1', 'security_blowfish_d', 'security_blowfish_e', 'security_rijndael_d', 'security_rijndael_e']
    server='cpu'

if args.device == '6':
    bens=['telecom_gsm', 'security_blowfish_e'] #,'security_sha'
    bens=['security_sha', 'telecom_CRC32', 'telecom_adpcm_c', 'telecom_adpcm_d', 'telecom_gsm']
    server = 'cuda' 
    cuda_number = 1
    

t1=time.time()
# methods = ['random','one-for-all-random','O3']
methods = ['perf']
# methods = ['cost_model']
# methods = ['cost_model', 'collect_pmu']
# methods = ['O3']
# methods = ['adaptive_local','one-for-all-nevergrad','random-len100']
# methods = ['one-by-one','nevergrad','opentuner']

epochs=1
for i in range(epochs):
    for method in methods:
        if method == 'one-by-one':
            budget = 3000
        elif method == 'adaptive_local' or method == 'random-len100':
            budget = 2000
        else:
            budget = 2000

        t0=time.time()
        for benchmark in bens:
            print('='*20)
            print(benchmark, method, i)
            if server=='cuda':
                cmd =  f'CUDA_VISIBLE_DEVICES={cuda_number} python run_cBench_ssh.py --device={args.device} --method={method} --benchmark={benchmark} --budget={budget} --server={server}'
            else:
                cmd = f'python run_cBench_ssh.py --device={args.device} --method={method} --benchmark={benchmark} --budget={budget} --server={server}'
            subprocess.run(cmd, shell=True)
        print(f'time of epoch {i} {method} budget {args.budget}:',time.time()-t0)
print('total time:',time.time()-t1)


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
parser.add_argument('--budget', type=int,default=215, help='')
parser.add_argument('--n-parallel', type=int,default=50, help='')
parser.add_argument('--batch-size', type=int, default=1)
args = parser.parse_args()

# ben2num=['automotive_bitcount', 'automotive_qsort1','automotive_susan_c', 'automotive_susan_e', 'automotive_susan_s','bzip2d','bzip2e','consumer_jpeg_c','consumer_lame', 'consumer_tiffmedian','network_dijkstra','network_patricia','office_rsynth','security_blowfish_d', 'security_blowfish_e', 'security_sha', 'telecom_adpcm_c','telecom_adpcm_d', 'telecom_CRC32', 'telecom_gsm']
final_benchmarks = ['automotive_bitcount', 'automotive_qsort1', 'bzip2d', 'bzip2e', 'consumer_jpeg_c', 'consumer_jpeg_d', 'consumer_lame', 'consumer_tiff2bw', 'consumer_tiff2rgba', 'security_blowfish_d', 'security_blowfish_e', 'security_sha','telecom_gsm']

if args.device == '1':
    bens=['automotive_bitcount', 'automotive_qsort1','bzip2d']
    # bens=['automotive_susan_e']
if args.device == '3':
    bens=['bzip2e', 'consumer_jpeg_c', 'consumer_jpeg_d']
    # bens=['bzip2e']
# if args.device == '3':
#     bens=['consumer_lame', 'consumer_tiffmedian','network_dijkstra','network_patricia']
#     # bens=['consumer_lame', 'consumer_tiffmedian']
if args.device == '4':
    bens=['consumer_lame', 'consumer_tiff2bw']

if args.device == '5':
    bens=['consumer_tiff2rgba', 'security_blowfish_d']
    # bens=['office_rsynth']
if args.device == '6':
    bens=['security_blowfish_e', 'security_sha','telecom_gsm']
    # bens=['telecom_gsm']

t1=time.time()
methods = ['random','one-for-all-random']
epochs=20
for i in range(epochs):
    for method in methods:
        t0=time.time()
        for benchmark in bens:
            print('='*20)
            print(benchmark, method, i)
            subprocess.run(f'python run_cBench_ssh.py --device={args.device} --method={method} --benchmark={benchmark} --budget={args.budget}', shell=True)
        print(f'time of epoch {i} {method} budget {args.budget}:',time.time()-t0)
print('total time:',time.time()-t1)

        

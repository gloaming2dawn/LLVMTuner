# -*- coding: utf-8 -*-
"""
Created on Wed Mar  2 17:54:48 2022

@author: scjzhadmin
"""
# gsm O0 pmu出错
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

# python run_cBench_ssh.py --device=1 --method=O3 --benchmark=automotive_bitcount --budget=50
# python run_cBench_ssh.py --device=1 --method=adaptive_local --benchmark=automotive_bitcount --budget=2000
# python run_cBench_ssh.py --device=6 --method=BO --benchmark=telecom_gsm --budget=1000 --device=cuda
# python run_cBench_ssh.py --device=4 --method=adaptive_local --benchmark=consumer_lame --budget=3000
# python run_cBench_ssh.py --device=6 --method=test_best --benchmark=security_sha
# python run_cBench_ssh.py --device=6 --method=cost_model --budget=2000 --benchmark=security_sha


parser = argparse.ArgumentParser()
parser.add_argument('--device', required=True, help='')
parser.add_argument('--method', required=True, help='')
parser.add_argument('--benchmark', required=True, help='')
parser.add_argument('--budget', type=int,default=50, help='')
parser.add_argument('--n-parallel', type=int,default=50, help='')
parser.add_argument('--batch-size', type=int, default=1)
parser.add_argument('--server', default='cpu')
args = parser.parse_args()

passes, passes_clear, pass2kind, O3_trans_seq=default_space()
# passes=llvmtuner.searchspace.compilergym_space()
# passes.append('')



# ben2num={'automotive_bitcount':5, 'automotive_qsort1': 10,'automotive_susan_c':50, 'automotive_susan_e':20, 'automotive_susan_s':5,'bzip2d':3,'bzip2e':2,'consumer_jpeg_c':100,'consumer_lame':10, 'consumer_tiffmedian':200,'network_dijkstra':100000,'network_patricia':5000,'security_blowfish_d':5000, 'security_blowfish_e':5000, 'security_sha':8000, 'telecom_adpcm_c':500,'telecom_adpcm_d':1000, 'telecom_CRC32':50, 'telecom_gsm':40, 'consumer_jpeg_d':100, 'consumer_tiff2bw':100, 'consumer_tiff2rgba':60, 'office_stringsearch1': 100000, 'consumer_tiffdither': 150, 'security_rijndael_d':1000, 'security_rijndael_e':1000} 

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
# run_cmd = './__run 1 {}'.format(ben2num[args.benchmark])
# run_cmd = './__run 3 1' 
# run_cmd = './__run 15 5' 
# run_cmd = './__run 3 1'
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
            ret=sshC.run(f'timeout {timeout_seconds} {perf_cmd} {run_cmd}' , hide=True, timeout=timeout_seconds) 
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
        searchObj = re.search( r'real\s*(.*)m(.*)s.*', temp)
        runtime = int(searchObj[1])*60+float(searchObj[2])



    except invoke.exceptions.UnexpectedExit:
        runtime = inf
    except invoke.exceptions.CommandTimedOut:
        runtime = inf   

    lines = temp.strip().split('\n')
    features = {}
    for line in lines:
        match = re.search(r'(\d+(?:,\d+)*)\s+(\w+(?:-\w+)*)', line)
        if match:
            value = match.group(1).replace(',', '')
            key = match.group(2)
            features[key] = int(value)
    
    pmu_events = 'branch-misses,cache-misses,cache-references,cpu-cycles,instructions,cpu-clock,L1-dcache-load-misses,L1-dcache-loads,L1-dcache-store-misses,L1-dcache-stores,branch-load-misses,branch-loads'.split(',')
    pmu = {k: features[k] for k in pmu_events}     
    
    return pmu


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
fun_O3.build('default<O3>')
print('O3 compilation time:',time.time()-t0)
# fun_O3('default<O3>')



hotfiles=ben2hot[args.benchmark]
fun = Function_wrap(ccmd, ben_dir, tmp_dir, run_and_eval_fun, hotfiles)#, profdata=os.path.join(ben_dir, 'default.profdata')
# fun.repeat = 1
# fun.adaptive_measure = False
len_seq=150



if __name__ == "__main__":
    if args.method == 'O0':
        # f.hotfiles =allfiles
        fun.repeat = 1
        fun.adaptive_measure = False
        y = fun('default<O0>')

    if args.method == 'O1':
        # f.hotfiles =allfiles
        fun.repeat = 5
        fun.adaptive_measure = False
        y = fun('default<O1>')
    
    if args.method == 'O2':
        # f.hotfiles =allfiles
        y = fun('default<O2>')
    
    if args.method == 'O3_seq':
        # f.hotfiles = allfiles
        y = fun(' '.join(O3_trans_seq))

    if args.method == 'O3':
        # f.hotfiles = allfiles
        fun.repeat = 10
        fun.adaptive_measure = False
        y = fun('default<O3>')
    
    if args.method == 'O3/O1':
        # f.hotfiles = allfiles
        fun.repeat = 5
        fun.adaptive_measure = False
        y_O1 = fun('default<O1>')
        y_O3 = fun('default<O3>')
        print('O3/O1 speedup',y_O1/y_O3)
    
    if args.method == 'perf':
        module2funcnames = fun_O3._get_func_names()
        fun_O3.repeat = 1
        fun_O3('default<O3>')
        folded_perf_result = perf_record(sshC, ben_dir, run_dir, run_cmd)
        hotfiles,hotfiles_details = gen_hotfiles(module2funcnames, binary_name, folded_perf_result)
        print(hotfiles, hotfiles_details)
        with open(f'{args.benchmark}_hotfiles.json','w') as file:
            json.dump(hotfiles_details, file, indent=4)
    
    if args.method == 'cost_model':
        pmu_savepath = os.path.join(tmp_dir, 'pmu_O3.txt')
        pmu_cmd = f'python collect_PMU.py --device={args.device} --benchmark={args.benchmark} --optlevel=O3 2> {pmu_savepath}'
        subprocess.run(pmu_cmd, shell=True)

        pmu_savepath = os.path.join(tmp_dir, 'pmu_O0.txt')
        pmu_cmd = f'python collect_PMU.py --device={args.device} --benchmark={args.benchmark} --optlevel=O0 2> {pmu_savepath}'
        subprocess.run(pmu_cmd, shell=True)

        # hotfiles=ben2hot[args.benchmark]
        # hotfiles = hotfiles[:1]
        # fun = Function_wrap(ccmd, ben_dir, tmp_dir, run_and_eval_fun, hotfiles)
        # len_seq=120


        # params={}
        # filename = fun.hotfiles[0]
        # fileroot,fileext=os.path.splitext(filename)
        # for ii in range(args.budget):
        #     seq=random.choices(passes, k=len_seq)
        #     params[fileroot]=passlist2str(deepcopy(seq))
        #     y = fun(deepcopy(params))


    if args.method == 'collect_pmu':
        hotfiles=ben2hot[args.benchmark]
        hotfiles = hotfiles[:1]
        fun = Function_wrap(ccmd, ben_dir, tmp_dir, run_and_eval_fun, hotfiles)
        data_path = f'/home/jiayu/result_llvmtuner_17/cBench/{args.benchmark}'
        with open(f'{data_path}/cost_model/result.json','r') as file:
            ic = 0
            for line in file:
                # 将每行的内容从JSON字符串转换为列表
                cfgpath, time = json.loads(line)
                with open(cfgpath, 'r') as file:
                    cfg=json.load(file)
                fun.build(cfg['params'])
                pmu = collect_pmu()
                cfg['pmu'] = pmu
                with open(cfgpath, 'w') as file:
                    json.dump(cfg, file, indent=4)
                ic = ic+1
                print(ic, cfgpath)
                

                


        






    
    # if args.method == 'O3-random':
    #     def random_params():
    #         params={}
    #         for filename in fun.hotfiles:
    #             fileroot,fileext=os.path.splitext(filename)
    #             seq=random.choices(passes, k=len_seq)
    #             seq=check_seq(seq)
    #             params[fileroot]='-O3 ' + ' '.join(seq)
    #         return params
        
    #     params_list = []
    #     for _ in range(args.budget):
    #         params = random_params()
    #         params_list.append(params)
        
    #     t0 = time.time()
    #     with Pool(50) as p:
    #         flags = p.map(fun.gen_optIR, params_list)
    #     print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        
    #     for i in range(len(params_list)):
    #         if flags[i]:
    #             y = fun(params_list[i])
        
    #     print(f'{args.benchmark} {args.budget} iterations cost:',time.time()-t0)


    if args.method=='random':
        def random_params(i):
            params={}
            for filename in fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                seq=random.choices(passes, k=len_seq)
                params[fileroot]=passlist2str(deepcopy(seq))
            return params
        
        params_list = []
        t0 = time.time()
        with Pool(50) as p:
            params_list = list(p.map(random_params, range(args.budget)))

        # for _ in range(args.budget):
        #     params = random_params()
        #     params_list.append(params)
        print(f'time of generating params:',time.time()-t0)
        
        t0 = time.time()
        with Pool(50) as p:
            flags = p.map(fun.gen_optIR, params_list)
        print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        print(f"Number of successful compilation: {sum(flags)}")

        
        for i in range(len(params_list)):
            if flags[i]:
                y = fun(params_list[i])
        
        print(f'{args.benchmark} {args.budget} iterations cost:',time.time()-t0)
    
    if args.method=='random-all':
        def random_params(i):
            params={}
            for filename in fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                seq=random.choices(passes, k=len_seq)
                params[fileroot]=passlist2str(deepcopy(seq))
            return params
        
        params_list = []
        t0 = time.time()
        with Pool(50) as p:
            params_list = list(p.map(random_params, range(args.budget)))

        # for _ in range(args.budget):
        #     params = random_params()
        #     params_list.append(params)
        print(f'time of generating params:',time.time()-t0)
        
        t0 = time.time()
        with Pool(50) as p:
            flags = p.map(fun.gen_optIR, params_list)
        print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        print(f"Number of successful compilation: {sum(flags)}")

        
        for i in range(len(params_list)):
            if flags[i]:
                y = fun(params_list[i])
        
        print(f'{args.benchmark} {args.budget} iterations cost:',time.time()-t0)
    
    if args.method=='random-len100':
        len_seq = 100
        def random_params(i):
            params={}
            for filename in fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                seq=random.choices(passes, k=len_seq)
                params[fileroot]=passlist2str(deepcopy(seq))
            return params
        
        params_list = []
        t0 = time.time()
        with Pool(50) as p:
            params_list = list(p.map(random_params, range(args.budget)))

        # for _ in range(args.budget):
        #     params = random_params()
        #     params_list.append(params)
        print(f'time of generating params:',time.time()-t0)
        
        t0 = time.time()
        with Pool(50) as p:
            flags = p.map(fun.gen_optIR, params_list)
        print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        print(f"Number of successful compilation: {sum(flags)}")

        
        for i in range(len(params_list)):
            if flags[i]:
                y = fun(params_list[i])
        
        print(f'{args.benchmark} {args.budget} iterations cost:',time.time()-t0)
    
    if args.method=='random-len80':
        len_seq = 80
        def random_params(i):
            params={}
            for filename in fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                seq=random.choices(passes, k=len_seq)
                params[fileroot]=passlist2str(deepcopy(seq))
            return params
        
        params_list = []
        t0 = time.time()
        with Pool(50) as p:
            params_list = list(p.map(random_params, range(args.budget)))

        # for _ in range(args.budget):
        #     params = random_params()
        #     params_list.append(params)
        print(f'time of generating params:',time.time()-t0)
        
        t0 = time.time()
        with Pool(50) as p:
            flags = p.map(fun.gen_optIR, params_list)
        print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        print(f"Number of successful compilation: {sum(flags)}")

        
        for i in range(len(params_list)):
            if flags[i]:
                y = fun(params_list[i])
        
        print(f'{args.benchmark} {args.budget} iterations cost:',time.time()-t0)
        
            
            
    if args.method=='one-for-all-random': 
        def random_params_one(i):
            seq=random.choices(passes, k=len_seq)
            for filename in fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                params=passlist2str(deepcopy(seq))
            return params
        
        params_list=[]
        t0 = time.time()
        with Pool(50) as p:
            params_list = list(p.map(random_params_one, range(args.budget)))
        print(f'time of generating params:',time.time()-t0)
        # for _ in range(args.budget):
        #     params = random_params_one()
        #     params_list.append(params)
            # y = f(' '.join(seq))
        
        t0 = time.time()
        with Pool(50) as p:
            flags = p.map(fun.gen_optIR, params_list)
        print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        print(f"Number of successful compilation: {sum(flags)}")
        
        for i in range(len(params_list)):
            if flags[i]:
                y = fun(params_list[i])
        print(f'{args.benchmark} {args.budget} iterations cost:',time.time()-t0)



    
    if args.method=='test_best':
        methods = ['adaptive_local','nevergrad','random','one-by-one','one-for-all-random','one-for-all-nevergrad']
        # methods = ['random']
        y_O3 = fun('default<O3>')
        for method in methods:
            config_times = []
            # shortest_time = float('inf')
            with open(f'/home/jiayu/result_llvmtuner_17/data1-cBench/{args.benchmark}/{method}/result.json','r') as file:
                for line in file:
                    # 将每行的内容从JSON字符串转换为列表
                    config, time = json.loads(line)
                    config_times.append((config, time))
                    # # 检查运行时间是否为最短
                    # if time < shortest_time:
                    #     shortest_time = time
                    #     shortest_config = config
            sorted_config_times = sorted(config_times, key=lambda x: x[1])
            shortest_config, shortest_time = sorted_config_times[0]
            print(shortest_config, shortest_time)
            shortest_config = shortest_config.replace('cBench','data1-cBench')
            print(shortest_config)
            with open(shortest_config,'r') as file:
                data = json.load(file)
                params = data['params']
            
            fun.repeat = 10
            fun.adaptive_measure = False
            y = fun(params)
            print(method, y, y_O3/y)
            # print('speedup',y_O3/y)
        



    if args.method=='tab1':
        config_times = []
        # shortest_time = float('inf')
        with open('/home/jiayu/result_llvmtuner_17/cBench/telecom_gsm/one-for-all-random/result.json','r') as file:
            for line in file:
                # 将每行的内容从JSON字符串转换为列表
                config, time = json.loads(line)
                config_times.append((config, time))
                # # 检查运行时间是否为最短
                # if time < shortest_time:
                #     shortest_time = time
                #     shortest_config = config
        sorted_config_times = sorted(config_times, key=lambda x: x[1])
        shortest_config, shortest_time = sorted_config_times[0]
        print(shortest_config, shortest_time)
        with open(shortest_config,'r') as file:
            data = json.load(file)
            opt_str = data['params']


        str1 = 'default<O3>'
        str2 = opt_str

        # str1 = 'default<O3>'
        # str2 = 'default<O1>'

        params_O3={}
        for filename in fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            params_O3[fileroot] = 'default<O3>'
        fun.repeat = 10
        fun.adaptive_measure = False
        # y = fun(params_O3)


        params=deepcopy(params_O3)
        params['long_term'] = str1
        params['short_term'] = str1
        y = fun(params)
        print(f'long_term: str1, short_term:str1',y)

        # id = hashlib.md5(params['long_term'].encode('utf-8')).hexdigest()
        # obj1 = os.path.join(tmp_dir, 'long_term', f'IR-{id}','long_term.o')
        # id = hashlib.md5(params['short_term'].encode('utf-8')).hexdigest()
        # obj2 = os.path.join(tmp_dir, 'short_term', f'IR-{id}','short_term.o')
        # exe = os.path.join(ben_dir, 'a.out')
        # tab1_dir = os.path.join(tmp_dir, 'LLVMTuner-cfg', f'{params["long_term"]}_{params["short_term"]}')
        # os.makedirs(tab1_dir, exist_ok=True)
        # subprocess.run(f'cp {obj1} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {obj2} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {exe} {tab1_dir}', shell=True)
        # objs_others = []
        # for filename in allfiles:
        #     fileroot,fileext=os.path.splitext(filename)
        #     obj = os.path.join(ben_dir, f'{fileroot}.o')
        #     objs_others.append(obj)
        #     if fileroot in ['long_term']:
        #         subprocess.run(f'diff {obj1} {obj}', shell=True)
        
        # exe2 = os.path.join(tab1_dir, 'b.out')
        # # subprocess.run(f'clang {obj1} {obj2} {" ".join(objs_others)} {cross_flags} -o {exe2}', shell=True)
        # subprocess.run(f'clang {" ".join(objs_others)} {cross_flags} -lm -o {exe2}', shell=True)
        # subprocess.run(f'diff {exe} {exe2}', shell=True)

        

        params=deepcopy(params_O3)
        params['long_term'] = str2
        params['short_term'] = str1
        y = fun(params)
        print(f'long_term:str2, short_term:str1',y)

        # id = hashlib.md5(params['long_term'].encode('utf-8')).hexdigest()
        # obj1 = os.path.join(tmp_dir, 'long_term', f'IR-{id}','long_term.o')
        # id = hashlib.md5(params['short_term'].encode('utf-8')).hexdigest()
        # obj2 = os.path.join(tmp_dir, 'short_term', f'IR-{id}','short_term.o')
        # exe = os.path.join(ben_dir, 'a.out')
        # tab1_dir = os.path.join(tmp_dir, 'LLVMTuner-cfg', f'{params["long_term"]}_{params["short_term"]}')
        # os.makedirs(tab1_dir, exist_ok=True)
        # subprocess.run(f'cp {obj1} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {obj2} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {exe} {tab1_dir}', shell=True)
        # objs_others = []
        # for filename in allfiles:
        #     fileroot,fileext=os.path.splitext(filename)
        #     obj = os.path.join(ben_dir, f'{fileroot}.o')
        #     objs_others.append(obj)
        #     if fileroot in ['long_term']:
        #         subprocess.run(f'diff {obj1} {obj}', shell=True)
        
        # exe2 = os.path.join(tab1_dir, 'b.out')
        # # subprocess.run(f'clang {obj1} {obj2} {" ".join(objs_others)} {cross_flags} -o {exe2}', shell=True)
        # subprocess.run(f'clang {" ".join(objs_others)} {cross_flags} -lm -o {exe2}', shell=True)
        # subprocess.run(f'diff {exe} {exe2}', shell=True)


        params=deepcopy(params_O3)
        params['long_term'] = str1
        params['short_term'] = str2
        y = fun(params)
        print(f'long_term:str1, short_term:str2',y)

        # id = hashlib.md5(params['long_term'].encode('utf-8')).hexdigest()
        # obj1 = os.path.join(tmp_dir, 'long_term', f'IR-{id}','long_term.o')
        # id = hashlib.md5(params['short_term'].encode('utf-8')).hexdigest()
        # obj2 = os.path.join(tmp_dir, 'short_term', f'IR-{id}','short_term.o')
        # exe = os.path.join(ben_dir, 'a.out')
        # tab1_dir = os.path.join(tmp_dir, 'LLVMTuner-cfg', f'{params["long_term"]}_{params["short_term"]}')
        # os.makedirs(tab1_dir, exist_ok=True)
        # subprocess.run(f'cp {obj1} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {obj2} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {exe} {tab1_dir}', shell=True)
        # objs_others = []
        # for filename in allfiles:
        #     fileroot,fileext=os.path.splitext(filename)
        #     obj = os.path.join(ben_dir, f'{fileroot}.o')
        #     objs_others.append(obj)
        #     if fileroot in ['long_term']:
        #         subprocess.run(f'diff {obj1} {obj}', shell=True)
        
        # exe2 = os.path.join(tab1_dir, 'b.out')
        # # subprocess.run(f'clang {obj1} {obj2} {" ".join(objs_others)} {cross_flags} -o {exe2}', shell=True)
        # subprocess.run(f'clang {" ".join(objs_others)} {cross_flags} -lm -o {exe2}', shell=True)
        # subprocess.run(f'diff {exe} {exe2}', shell=True)


        params=deepcopy(params_O3)
        params['long_term'] = str2
        params['short_term'] = str2
        y = fun(params)
        print(f'long_term:str2, short_term:str2',y)

        # id = hashlib.md5(params['long_term'].encode('utf-8')).hexdigest()
        # obj1 = os.path.join(tmp_dir, 'long_term', f'IR-{id}','long_term.o')
        # id = hashlib.md5(params['short_term'].encode('utf-8')).hexdigest()
        # obj2 = os.path.join(tmp_dir, 'short_term', f'IR-{id}','short_term.o')
        # exe = os.path.join(ben_dir, 'a.out')
        # tab1_dir = os.path.join(tmp_dir, 'LLVMTuner-cfg', f'{params["long_term"]}_{params["short_term"]}')
        # os.makedirs(tab1_dir, exist_ok=True)
        # subprocess.run(f'cp {obj1} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {obj2} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {exe} {tab1_dir}', shell=True)
        # objs_others = []
        # for filename in allfiles:
        #     fileroot,fileext=os.path.splitext(filename)
        #     obj = os.path.join(ben_dir, f'{fileroot}.o')
        #     objs_others.append(obj)
        #     if fileroot in ['long_term']:
        #         subprocess.run(f'diff {obj1} {obj}', shell=True)
        
        # exe2 = os.path.join(tab1_dir, 'b.out')
        # # subprocess.run(f'clang {obj1} {obj2} {" ".join(objs_others)} {cross_flags} -o {exe2}', shell=True)
        # subprocess.run(f'clang {" ".join(objs_others)} {cross_flags} -lm -o {exe2}', shell=True)
        # subprocess.run(f'diff {exe} {exe2}', shell=True)



    


    if args.method=='one-by-one':
        def allocate_budget(data, budget):
            # 计算总值
            total_value = sum(data.values())
            
            # 初始化结果字典
            result = {}
            
            # 根据值将预算分配给不同的键
            for key, value in data.items():
                result[key] = int(budget * (value / total_value))
            
            return result

        with open(f'{args.benchmark}_hotfiles.json', 'r') as file:
            data = json.load(file)
            d = {}
            for item in data:
                d[item[0]] = item[1]
            budgets = allocate_budget(d, args.budget)

        params={}
        for filename in fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            params[fileroot] = 'default<O3>'
        y = fun(params)

        for filename in fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            params=deepcopy(fun.best_params)
            for ii in range(budgets[fileroot]):
                seq=random.choices(passes, k=len_seq)
                params[fileroot]=passlist2str(deepcopy(seq))
                print(fileroot, ii, budgets[fileroot])
                y = fun(deepcopy(params))
            
            
                
        
                
        
    
    if args.method=='nevergrad':
        import nevergrad as ng
        import numpy as np
        len_seq = 100
        # optimizers = ng.optimizers.registry.keys()
        # print(list(optimizers))
        params_set = ng.p.Choice(
                choices=passes,
                repetitions=len_seq*len(fun.hotfiles),
                deterministic=True
            )
        
        optimizer=ng.optimizers.NGOpt(parametrization=params_set, budget=args.budget)
        # print(optimizer._select_optimizer_cls())

        def split_list(lst, num_chunks):
            avg = len(lst) // num_chunks
            return [lst[i:i+avg] for i in range(0, len(lst), avg)]

        count = 0
        previous_pass_list = ['*']*len_seq*len(fun.hotfiles)
        best_pass_list = ['*']*len_seq*len(fun.hotfiles)
        while count < args.budget:
            # if count <10:
            #     optimizer.suggest(random.choices(passes, k=len_seq*len(fun.hotfiles)))
            t0=time.time()
            x = optimizer.ask()
            print(f'ask time:',time.time()-t0)
            pass_list=list(x.value)
            n_changed = 0
            sum_changed = 0
            for i in range(len(pass_list)):
                if pass_list[i] != best_pass_list[i]:
                    n_changed += 1
                    sum_changed += i
            print(f'number of changed elements:',n_changed)
            print(f'sum of changed elements number:',sum_changed)
            previous_pass_list = pass_list

            seq_list = split_list(pass_list, len(fun.hotfiles))
            
            assert len(seq_list) == len(fun.hotfiles)
            params = {}
            for i in range(len(seq_list)):
                opt_str=passlist2str(seq_list[i])
                fileroot,fileext=os.path.splitext(fun.hotfiles[i])
                params[fileroot]=opt_str

            best_y = fun.best_y
            y=fun(params)
            if y != inf:
                t0=time.time()
                if y < best_y:
                    print(f'new best y:',y)
                    best_pass_list = pass_list
                optimizer.tell(x, y)
                print(f'tell time:',time.time()-t0)
                count += 1
                

    if args.method=='one-by-one-nevergrad':
        import nevergrad as ng
        import numpy as np
        # optimizers = ng.optimizers.registry.keys()
        # print(list(optimizers))
        params_set = ng.p.Choice(
                choices=passes,
                repetitions=len_seq,
                deterministic=True
            )
        
        params={}
        for filename in fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            params[fileroot] = 'default<O3>'
        y = fun(params)

        for filename in fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            params=deepcopy(fun.best_params)
            while count < args.budget:
                t0=time.time()
                x = optimizer.ask()
                print(f'ask time:',time.time()-t0)
                pass_list=list(x.value)
                params[fileroot]=passlist2str(deepcopy(pass_list))
                y = fun(deepcopy(params))
        
        optimizer=ng.optimizers.NGOpt(parametrization=params_set, budget=args.budget)
        # print(optimizer._select_optimizer_cls())

        

        count = 0
        previous_pass_list = ['*']*len_seq*len(fun.hotfiles)
        while count < args.budget:
            # if count <10:
            #     optimizer.suggest(random.choices(passes, k=len_seq*len(fun.hotfiles)))
            t0=time.time()
            x = optimizer.ask()
            print(f'ask time:',time.time()-t0)
            pass_list=list(x.value)
            n_changed = 0
            for i in range(len(pass_list)):
                if pass_list[i] != previous_pass_list[i]:
                    n_changed += 1
            print(f'number of changed elements:',n_changed)
            previous_pass_list = pass_list

            
                

            seq_list = split_list(pass_list, len(fun.hotfiles))
            
            assert len(seq_list) == len(fun.hotfiles)
            params = {}
            for i in range(len(seq_list)):
                opt_str=passlist2str(seq_list[i])
                fileroot,fileext=os.path.splitext(fun.hotfiles[i])
                params[fileroot]=opt_str
            
            y=fun(params)
            if y != inf:
                t0=time.time()
                optimizer.tell(x, y)
                print(f'tell time:',time.time()-t0)
                count += 1

    if args.method=='one-for-all-nevergrad':
        import nevergrad as ng
        import numpy as np
        # optimizers = ng.optimizers.registry.keys()
        # print(list(optimizers))
        params_set = ng.p.Choice(
                choices=passes,
                repetitions=len_seq,
                deterministic=True
            )
        
        optimizer=ng.optimizers.NGOpt(parametrization=params_set, budget=args.budget)
        # print(optimizer._select_optimizer_cls())

        count = 0
        while count < args.budget:
            # if count <10:
            #     optimizer.suggest(random.choices(passes, k=len_seq*len(fun.hotfiles)))
            t0=time.time()
            x = optimizer.ask()
            print(f'ask time:',time.time()-t0)
            pass_list=list(x.value)
            params = passlist2str(pass_list)            
            y=fun(params)
            if y != inf:
                t0=time.time()
                optimizer.tell(x, y)
                print(f'tell time:',time.time()-t0)
                count += 1

    if args.method=='local':
        optimizer=Localoptimizer(
            fun=fun,
            passes=passes, 
            precompiled_path=tmp_dir,
            len_seq=len_seq,
            budget=args.budget, 
            n_init=20,
            failtol=50,
            )

        optimizer.minimize()

    if args.method=='adaptive_local':
        optimizer=Adalocaloptimizer(
            fun=fun,
            passes=passes, 
            precompiled_path=tmp_dir,
            len_seq=len_seq,
            budget=args.budget, 
            n_init=2,
            failtol=50,
            )

        optimizer.minimize()

    if args.method=='BO':
        config_times = []
        # shortest_time = float('inf')
        method = 'adaptive_local'
        with open(f'/home/jiayu/result_llvmtuner_17/cBench/{args.benchmark}/{method}/result.json','r') as file:
            for line in file:
                # 将每行的内容从JSON字符串转换为列表
                config, time = json.loads(line)
                config_times.append((config, time))
        sorted_config_times = sorted(config_times, key=lambda x: x[1])
        shortest_config, shortest_time = sorted_config_times[0]
        with open(shortest_config,'r') as file:
            data = json.load(file)
            best_params = data['params']

        initial_guess = {}
        for fileroot in best_params:
            if fileroot == 'long_term':
                initial_guess[fileroot] = best_params[fileroot]
            else:
                initial_guess[fileroot] = 'default<O3>'

        # fun(initial_guess)

        initial_guess = {'long_term': best_params['long_term']}
        fun.hotfiles = ['long_term.c']
        fun(initial_guess)

        BO=BO(
            fun=fun,
            passes=passes, 
            precompiled_path=tmp_dir,
            len_seq=len_seq,
            budget=args.budget, 
            acqf='EI',
            beta=1.96,
            n_parallel=args.n_parallel,
            n_init=20,
            failtol=50,
            min_cuda=20,
            device=args.server,
            initial_guess = initial_guess,
            )

        BO.minimize()

    
        
        
    if args.method == 'reduce':
        methods = ['adaptive_local','nevergrad']
        methods = ['one-by-one']
        m2best={}
        for method in methods:
            config_times = []
            # shortest_time = float('inf')
            with open(f'/home/jiayu/result_llvmtuner_17/cBench/{args.benchmark}/{method}/result.json','r') as file:
                for line in file:
                    # 将每行的内容从JSON字符串转换为列表
                    config, time = json.loads(line)
                    config_times.append((config, time))
            sorted_config_times = sorted(config_times, key=lambda x: x[1])
            shortest_config, shortest_time = sorted_config_times[0]
            print(shortest_config, shortest_time)
            m2best[method] = [shortest_time,shortest_config]
            with open(shortest_config,'r') as file:
                data = json.load(file)
                params = data['params']
            params, y_ref = fun.reduce_pass(params)
            cfg_path = os.path.join(fun.cfg_dir, 'cfg-{}.json'.format( hashlib.md5(str(params).encode('utf-8')).hexdigest()) )
            dirname=os.path.expanduser('~/LLVM17_reduced_cBench_result')
            file=os.path.join(dirname,f'{args.benchmark}_reduce_best.json')
            data=[method, cfg_path, y_ref]
            with open(file, 'a') as ff:
                ff.write(json.dumps(data)+'\n')
    
    if args.method == 'importance':
        filepath = f'/home/jiayu/LLVM17_reduced_cBench_result/{args.benchmark}_reduce_best.json'
        data = read_json_lines(filepath)
        cfg = data[0][1]


        with open(cfg,'r') as file:
            data = json.load(file)
            params = data['params']

        params = {"long_term": "function<eager-inv>(slp-vectorizer,loop(loop-deletion)),cgscc(devirt<4>(function<eager-inv;no-rerun>(mldst-motion<no-split-footer-bb>,libcalls-shrinkwrap,adce))),function<eager-inv>(loop-unroll<O3>),cgscc(devirt<4>(function<eager-inv;no-rerun>(adce))),recompute-globalsaa,cgscc(devirt<4>(function<eager-inv;no-rerun>(constraint-elimination,simplifycfg<bonus-inst-threshold=1;no-forward-switch-cond;switch-range-to-icmp;no-switch-to-lookup;keep-loops;no-hoist-common-insts;no-sink-common-insts;speculate-blocks;simplify-cond-branch>))),function<eager-inv>(lower-constant-intrinsics,lower-expect),cgscc(devirt<4>(function<eager-inv;no-rerun>(move-auto-init))),function<eager-inv>(lower-expect,loop-load-elim),cgscc(devirt<4>(function<eager-inv;no-rerun>(loop-mssa(simple-loop-unswitch<nontrivial;trivial>)))),function<eager-inv>(loop(loop-interchange),lower-expect),rel-lookup-table-converter,function<eager-inv>(sink,chr,simplifycfg<bonus-inst-threshold=1;no-forward-switch-cond;no-switch-range-to-icmp;no-switch-to-lookup;keep-loops;no-hoist-common-insts;no-sink-common-insts;speculate-blocks;simplify-cond-branch>,lowerinvoke,simplifycfg<bonus-inst-threshold=1;forward-switch-cond;switch-range-to-icmp;switch-to-lookup;no-keep-loops;hoist-common-insts;sink-common-insts;speculate-blocks;simplify-cond-branch>),cgscc(devirt<4>(function<eager-inv;no-rerun>(tailcallelim))),function<eager-inv>(simplifycfg<bonus-inst-threshold=1;forward-switch-cond;switch-range-to-icmp;switch-to-lookup;no-keep-loops;hoist-common-insts;sink-common-insts;speculate-blocks;simplify-cond-branch>,simplifycfg<bonus-inst-threshold=1;no-forward-switch-cond;switch-range-to-icmp;no-switch-to-lookup;keep-loops;no-hoist-common-insts;no-sink-common-insts;speculate-blocks;simplify-cond-branch>),cgscc(devirt<4>(function<eager-inv;no-rerun>(loop(loop-idiom)))),function<eager-inv>(ee-instrument),elim-avail-extern,cgscc(devirt<4>(function<eager-inv;no-rerun>(coro-elide))),function<eager-inv>(simplifycfg<bonus-inst-threshold=1;forward-switch-cond;switch-range-to-icmp;switch-to-lookup;no-keep-loops;hoist-common-insts;sink-common-insts;speculate-blocks;simplify-cond-branch>),cgscc(devirt<4>(function<eager-inv;no-rerun>(loop(loop-unroll-full)))),function<eager-inv>(sroa<modify-cfg>,lower-expect),cgscc(devirt<4>(function<eager-inv;no-rerun>(loop(loop-unroll-full),early-cse<memssa>))),function<eager-inv>(div-rem-pairs),cgscc(devirt<4>(function<eager-inv;no-rerun>(aggressive-instcombine,constraint-elimination))),constmerge,function<eager-inv>(loop(loop-deletion),loop-vectorize<no-interleave-forced-only;no-vectorize-forced-only;>,instsimplify,sroa<modify-cfg>,sink,slp-vectorizer),cgscc(devirt<4>(function<eager-inv;no-rerun>(libcalls-shrinkwrap,dse))),function<eager-inv>(simplifycfg<bonus-inst-threshold=1;no-forward-switch-cond;no-switch-range-to-icmp;no-switch-to-lookup;keep-loops;no-hoist-common-insts;no-sink-common-insts;speculate-blocks;simplify-cond-branch>),cgscc(devirt<4>(function<eager-inv;no-rerun>(loop-mssa(simple-loop-unswitch<nontrivial;trivial>,loop-rotate<header-duplication;no-prepare-for-lto>)))),called-value-propagation,cgscc(devirt<4>(function-attrs<skip-non-recursive>)),function<eager-inv>(instsimplify),cgscc(devirt<4>(function<eager-inv;no-rerun>(sccp,memcpyopt,libcalls-shrinkwrap))),deadargelim,cgscc(devirt<4>(function<eager-inv;no-rerun>(jump-threading,memcpyopt))),function<eager-inv>(instcombine<max-iterations=1000;no-use-loop-info>,chr,sroa<modify-cfg>,mem2reg),ipsccp,rpo-function-attrs,function<eager-inv>(vector-combine,tailcallelim),cgscc(devirt<4>(function<eager-inv;no-rerun>(loop(indvars)))),recompute-globalsaa,function<eager-inv>(instsimplify),cgscc(devirt<4>(function<eager-inv;no-rerun>(bdce))),function<eager-inv>(mem2reg),globalopt,cgscc(devirt<4>(function<eager-inv;no-rerun>(coro-elide,mldst-motion<no-split-footer-bb>))),function<eager-inv>(slp-vectorizer,tailcallelim),coro-early,cgscc(devirt<4>(function<eager-inv;no-rerun>(correlated-propagation),coro-split,function<eager-inv;no-rerun>(adce))),globalopt,function<eager-inv>(loop(loop-interchange)),cgscc(devirt<4>(function-attrs)),function<eager-inv>(loop-vectorize<no-interleave-forced-only;no-vectorize-forced-only;>),cgscc(devirt<4>(function<eager-inv;no-rerun>(constraint-elimination))),function<eager-inv>(early-cse<>),cgscc(devirt<4>(function<eager-inv;no-rerun>(instcombine<max-iterations=1000;no-use-loop-info>,sroa<modify-cfg>,gvn<>))),called-value-propagation,cgscc(devirt<4>(function<eager-inv;no-rerun>(loop-mssa(licm<no-allowspeculation>),adce))),globaldce,cgscc(devirt<4>(function<eager-inv;no-rerun>(memcpyopt,loop(loop-idiom)))),function<eager-inv>(loop(loop-interchange)),cgscc(devirt<4>(inline<only-mandatory>)),ipsccp,function<eager-inv>(vector-combine),ipsccp,cgscc(devirt<4>(function<eager-inv;no-rerun>(loop-mssa(simple-loop-unswitch<nontrivial;trivial>)))),function<eager-inv>(lower-expect,alignment-from-assumptions,div-rem-pairs,callsite-splitting),cgscc(devirt<4>(function<eager-inv;no-rerun>(loop-mssa(loop-simplifycfg)))),function<eager-inv>(simplifycfg<bonus-inst-threshold=1;forward-switch-cond;switch-range-to-icmp;switch-to-lookup;no-keep-loops;hoist-common-insts;sink-common-insts;speculate-blocks;simplify-cond-branch>,tailcallelim),globalopt,cgscc(devirt<4>(function<eager-inv;no-rerun>(move-auto-init))),forceattrs,openmp-opt,deadargelim,forceattrs,annotation2metadata,cgscc(devirt<4>(function<eager-inv;no-rerun>(mldst-motion<no-split-footer-bb>))),function<eager-inv>(lower-constant-intrinsics),cgscc(devirt<4>(function<eager-inv;no-rerun>(bdce))),inferattrs,cgscc(devirt<4>(function-attrs,function<eager-inv;no-rerun>(loop(loop-idiom)))),rpo-function-attrs,function<eager-inv>(simplifycfg<bonus-inst-threshold=1;no-forward-switch-cond;switch-range-to-icmp;no-switch-to-lookup;keep-loops;no-hoist-common-insts;no-sink-common-insts;speculate-blocks;simplify-cond-branch>),cgscc(devirt<4>(function<eager-inv;no-rerun>(vector-combine))),function<eager-inv>(lowerinvoke),cgscc(devirt<4>(argpromotion,coro-split)),function<eager-inv>(loop(loop-rotate<header-duplication;no-prepare-for-lto>)),ipsccp,cg-profile,cgscc(devirt<4>(function-attrs<skip-non-recursive>,function<eager-inv;no-rerun>(simplifycfg<bonus-inst-threshold=1;no-forward-switch-cond;switch-range-to-icmp;no-switch-to-lookup;keep-loops;no-hoist-common-insts;no-sink-common-insts;speculate-blocks;simplify-cond-branch>))),ipsccp,function<eager-inv>(loop-data-prefetch),cgscc(devirt<4>(function<eager-inv;no-rerun>(simplifycfg<bonus-inst-threshold=1;no-forward-switch-cond;switch-range-to-icmp;no-switch-to-lookup;keep-loops;hoist-common-insts;sink-common-insts;speculate-blocks;simplify-cond-branch>,correlated-propagation,bdce,simplifycfg<bonus-inst-threshold=1;no-forward-switch-cond;switch-range-to-icmp;no-switch-to-lookup;keep-loops;no-hoist-common-insts;no-sink-common-insts;speculate-blocks;simplify-cond-branch>))),function<eager-inv>(loop-data-prefetch),cgscc(devirt<4>(function<eager-inv;no-rerun>(libcalls-shrinkwrap)))", "short_term": "default<O3>", "preprocess": "default<O3>", "rpe": "default<O3>", "lpc": "default<O3>"}

        params, y_ref = fun.reduce_pass(params)


    

        
    
        
                    
            
        
        
        
        
        
        
   
    
   
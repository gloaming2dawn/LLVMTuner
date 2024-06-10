# -*- coding: utf-8 -*-

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
from llvmtuner.baselines.random import random_optimizer
from llvmtuner.baselines.nevergrad import nevergrad_optimizer
from llvmtuner.function_wrap import Function_wrap
from llvmtuner.gen_hotfiles import gen_hotfiles


parser = argparse.ArgumentParser()
parser.add_argument('--method', required=True, help='')
parser.add_argument('--benchmark', required=True, help='')
parser.add_argument('--budget', type=int,default=50, help='')
parser.add_argument('--n-parallel', type=int,default=50, help='')
parser.add_argument('--batch-size', type=int, default=1)
args = parser.parse_args()

passes=llvmtuner.searchspace.default_space()[0] #默认使用的pass

build_dir = os.path.expanduser(f'~/cBench_V1.1/{args.benchmark}/src_work/')
run_dir = build_dir
build_cmd = f'make ZCC=clangopt LDCC=clangopt -C {build_dir}'
tmp_dir = os.path.join(os.path.expanduser('~/local_result_llvmtuner/cBench/'), args.benchmark, args.method)
ben2cmd = {'automotive_bitcount': './__run 1 5', 'automotive_qsort1': './__run 1 10' ,'automotive_susan_c':'./__run 9 5', 'automotive_susan_e':'./__run 9 2', 'automotive_susan_s':'./__run 19 1','bzip2d':'./__run 12 1','bzip2e':'./__run 12 1','consumer_jpeg_c':'./__run 15 2','consumer_lame':'./__run 6 1', 'consumer_tiffmedian':'./__run 11 1','network_dijkstra':'./__run 10 1','network_patricia':'./__run 13 20','security_blowfish_d':'./__run 20 20', 'security_blowfish_e':'./__run 20 20', 'security_sha':'./__run 4 10', 'telecom_adpcm_c':'./__run 2 3','telecom_adpcm_d':'./__run 2 5', 'telecom_CRC32':'./__run 2 1', 'telecom_gsm':'./__run 6 1', 'consumer_jpeg_d':'./__run 3 1', 'consumer_tiff2bw':'./__run 3 1', 'consumer_tiff2rgba':'./__run 3 1', 'office_stringsearch1': './__run 4 50', 'consumer_tiffdither': './__run 3 1', 'security_rijndael_d':'./__run 4 1', 'security_rijndael_e':'./__run 4 1'}
run_cmd = ben2cmd[args.benchmark]
binary = os.path.join(build_dir, 'a.out')

# # 以下展示了如何自动获取热点文件，由于cBench的热点文件我们已经提前获取，因此不需要再次运行
# hotfiles, hotfiles_details = gen_hotfiles(build_cmd, build_dir, tmp_dir, run_cmd, run_dir, binary)
# print(hotfiles,hotfiles_details)
# os.makedirs('cBench_hotfiles', exist_ok=True)
# with open(f'./cBench_hotfiles/{args.benchmark}_hotfiles.json','w') as file:
#     json.dump(hotfiles_details, file, indent=4)


# these are automatically obtained by using "hotfiles, hotfiles_details = gen_hotfiles(build_cmd, build_dir, run_cmd, run_dir)"
ben2hot={'automotive_bitcount': ['bitcnts', 'bitcnt_4', 'bitcnt_3', 'bitcnt_2'], 'automotive_qsort1': ['qsort', 'qsort_large'], 'automotive_susan_c': ['susan'], 'automotive_susan_e': ['susan'], 'automotive_susan_s': ['susan'], 'bzip2d': ['bzlib', 'decompress'], 'bzip2e': ['blocksort', 'compress', 'bzlib'], 'consumer_jpeg_c': ['jcphuff', 'jcdctmgr', 'jfdctint', 'jccolor', 'jchuff', 'jccoefct'], 'consumer_jpeg_d': ['jidctint', 'jdhuff', 'jdcolor', 'jdsample'], 'consumer_lame': ['psymodel', 'newmdct', 'fft', 'quantize', 'takehiro','quantize-pvt', 'l3bitstream', 'formatBitstream'], 'consumer_tiff2bw': ['tif_lzw', 'tif_predict', 'tiff2bw'], 'consumer_tiff2rgba': ['tif_lzw', 'tif_getimage', 'tif_predict'], 'consumer_tiffmedian': ['tiffmedian'], 'network_dijkstra': ['dijkstra_large'], 'network_patricia': ['patricia'], 'office_stringsearch1': ['pbmsrch_large'], 'security_blowfish_d': ['bf_enc', 'bf_cfb64'], 'security_blowfish_e': ['bf_enc', 'bf_cfb64'], 'security_sha': ['sha'], 'telecom_CRC32': ['crc_32'], 'telecom_adpcm_c': ['adpcm'], 'telecom_adpcm_d': ['adpcm'], 'telecom_gsm': ['long_term', 'short_term', 'preprocess', 'rpe', 'lpc'], 'consumer_tiffdither':['tif_fax3','tiffdither','tif_lzw'], 'security_rijndael_d':['aes'], 'security_rijndael_e':['aes']}

hotfiles=ben2hot[args.benchmark]


fun = Function_wrap(
                    build_cmd=build_cmd, #编译命令，用户提供
                    build_dir=build_dir, #编译路径，用户提供
                    tmp_dir=tmp_dir, #数据存放目录，用户定义
                    run_cmd=run_cmd, #运行命令，用户提供
                    run_dir=run_dir, #运行路径，用户提供
                    binary=binary, #编译后的二进制文件路径，用户提供
                    # ssh_connection, #ssh连接
                    )
fun.build('default<O3>') # 首先不考虑热点文件在O3下编译，确保非热点文件均在O3下已编译，防止后续编译出错
fun.hotfiles = hotfiles # 然后加入热点文件，此后函数每次接受新的编译配置时，只会编译热点文件

if __name__ == "__main__":
    if args.method=='random': 
        optimizer=random_optimizer(fun=fun, passes=passes, budget=args.budget)
        best_cfg, best_cost = optimizer.minimize()
        print('best runtime:', best_cost)
    
    if args.method=='nevergrad':
        optimizer=nevergrad_optimizer(fun=fun, passes=passes, budget=args.budget)
        best_cfg, best_cost = optimizer.minimize()
        print('best runtime:', best_cost)
    
    if args.method=='BO':
        BO=BO(
                fun=fun,
                passes=passes, 
                budget=args.budget, 
                acqf='EI',
                n_init=5,
                max_cand_seqs = 200,
                device='cpu',
                )
        BO.minimize()

    if args.method=='O3':
        y = fun('default<O3>')
        print('O3 runtime:', y)


    
    
    
# if args.method=='ngopt':
#     import nevergrad as ng
#     params = ng.p.Choice(
#             choices=passes,
#             repetitions=len_seq,
#             deterministic=True
#         )
#     optimizer=ng.optimizers.NGOpt(parametrization=params, budget=args.budget, num_workers=1)
#     print(optimizer._select_optimizer_cls())
#     for i in range(args.budget):
#         x = optimizer.ask()
#         seq=list(x.value)
#         seq=check_seq(seq)
#         y=f(' '.join(seq))
#         if y != inf:
#             optimizer.tell(x, y)
        
# if args.method=='BO':
#     BO=BO(
#         fun=f,
#         passes=passes, 
#         len_seq=len_seq,
#         budget=args.budget, 
#         acqf='EI',# or UCB
#         beta=1.96,
#         n_parallel=args.n_parallel,
#         n_init=20,
#         )

#     BO.minimize()
        
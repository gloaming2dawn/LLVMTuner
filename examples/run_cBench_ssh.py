# -*- coding: utf-8 -*-

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
from llvmtuner.searchspace import default_space
from llvmtuner.BO.BO import BO
from llvmtuner.baselines.random import random_optimizer
from llvmtuner.baselines.nevergrad import nevergrad_optimizer
from llvmtuner.function_wrap import Function_wrap
from llvmtuner.gen_hotfiles import gen_hotfiles


# python run_cBench_ssh.py --device=1 --method=O3 --benchmark=automotive_bitcount --budget=50
# python run_cBench_ssh.py --device=1 --method=adaptive_local --benchmark=automotive_bitcount --budget=2000
# python run_cBench_ssh.py --device=6 --method=BO --benchmark=telecom_gsm --budget=1000 --device=cuda
# python run_cBench_ssh.py --device=4 --method=adaptive_local --benchmark=consumer_lame --budget=3000
# python run_cBench_ssh.py --device=6 --method=test_best --benchmark=security_sha
# python run_cBench_ssh.py --device=6 --method=cost_model --budget=2000 --benchmark=security_sha
# python run_cBench_ssh.py --method=random --benchmark=security_sha --budget=10  

parser = argparse.ArgumentParser()
parser.add_argument('--device', type=int, required=True)
parser.add_argument('--method', required=True, help='')
parser.add_argument('--benchmark', required=True, help='')
parser.add_argument('--budget', type=int,default=50, help='')
parser.add_argument('--n-parallel', type=int,default=50, help='')
parser.add_argument('--batch-size', type=int, default=1)
parser.add_argument('--server', default='cpu')
args = parser.parse_args()

passes, passes_clear, pass2kind, O3_trans_seq=default_space()


# network_dijkstra噪声太大，network_patricia噪声在3%
ben2cmd = {'automotive_bitcount': './__run 1 5', 'automotive_qsort1': './__run 1 10' ,'automotive_susan_c':'./__run 9 5', 'automotive_susan_e':'./__run 9 2', 'automotive_susan_s':'./__run 19 1','bzip2d':'./__run 12 1','bzip2e':'./__run 12 1','consumer_jpeg_c':'./__run 15 2','consumer_lame':'./__run 6 1', 'consumer_tiffmedian':'./__run 11 1','network_dijkstra':'./__run 10 1','network_patricia':'./__run 13 20','security_blowfish_d':'./__run 20 20', 'security_blowfish_e':'./__run 20 20', 'security_sha':'./__run 4 10', 'telecom_adpcm_c':'./__run 2 5','telecom_adpcm_d':'./__run 2 5', 'telecom_CRC32':'./__run 2 1', 'telecom_gsm':'./__run 6 1', 'consumer_jpeg_d':'./__run 3 1', 'consumer_tiff2bw':'./__run 3 1', 'consumer_tiff2rgba':'./__run 3 1', 'office_stringsearch1': './__run 4 50', 'consumer_tiffdither': './__run 3 1', 'security_rijndael_d':'./__run 4 1', 'security_rijndael_e':'./__run 4 1'}


ben2hot={'automotive_bitcount': ['bitcnts', 'bitcnt_4', 'bitcnt_3', 'bitcnt_2'], 'automotive_qsort1': ['qsort', 'qsort_large'], 'automotive_susan_c': ['susan'], 'automotive_susan_e': ['susan'], 'automotive_susan_s': ['susan'], 'bzip2d': ['bzlib', 'decompress'], 'bzip2e': ['blocksort', 'compress', 'bzlib'], 'consumer_jpeg_c': ['jcphuff', 'jcdctmgr', 'jfdctint', 'jccolor', 'jchuff', 'jccoefct'], 'consumer_jpeg_d': ['jidctint', 'jdhuff', 'jdcolor', 'jdsample'], 'consumer_lame': ['psymodel', 'newmdct', 'fft', 'quantize', 'takehiro','quantize-pvt', 'l3bitstream', 'formatBitstream'], 'consumer_tiff2bw': ['tif_lzw', 'tif_predict', 'tiff2bw'], 'consumer_tiff2rgba': ['tif_lzw', 'tif_getimage', 'tif_predict'], 'consumer_tiffmedian': ['tiffmedian'], 'network_dijkstra': ['dijkstra_large'], 'network_patricia': ['patricia'], 'office_stringsearch1': ['pbmsrch_large'], 'security_blowfish_d': ['bf_enc', 'bf_cfb64'], 'security_blowfish_e': ['bf_enc', 'bf_cfb64'], 'security_sha': ['sha'], 'telecom_CRC32': ['crc_32'], 'telecom_adpcm_c': ['adpcm'], 'telecom_adpcm_d': ['adpcm'], 'telecom_gsm': ['long_term', 'short_term', 'preprocess', 'rpe', 'lpc'], 'consumer_tiffdither':['tif_fax3','tiffdither','tif_lzw'], 'security_rijndael_d':['aes'], 'security_rijndael_e':['aes']}
hotfiles=ben2hot[args.benchmark]

cross_flags='--target=aarch64-linux-gnu --sysroot=/home/jiayu/gcc-4.8.5-aarch64/install/aarch64-unknown-linux-gnu/sysroot/ --gcc-toolchain=/home/jiayu/gcc-4.8.5-aarch64/install' #用户应替换为对应平台下的交叉编译工具链
build_dir = os.path.expanduser(f'~/cBench_V1.1/{args.benchmark}/src_work/')
build_cmd = f'make ZCC=clangopt LDCC=clangopt CCC_OPTS="{cross_flags}" LD_OPTS="{cross_flags}" -C {build_dir}'#用户应替换为相应的交叉编译命令


tmp_dir = os.path.join(os.path.expanduser('~/result_llvmtuner_17_arm/cBench/'), args.benchmark, args.method)
binary = os.path.join(build_dir, 'a.out')

ssh_connection=Connection(host=f'nvidia@TX2-{args.device}.local') #用户应替换为相应的ssh连接，支持多次跳转，参阅fabric的API
run_dir = '/home/nvidia/cBench_V1.1/{}/src_work/'.format(args.benchmark) #用户应替换为相应的运行路径
run_cmd = ben2cmd[args.benchmark]


# # 以下展示了如何自动获取热点文件，由于cBench的热点文件我们已经提前获取，因此不需要再次运行
# hotfiles, hotfiles_details = gen_hotfiles(build_cmd, build_dir, tmp_dir, run_cmd, run_dir, binary, ssh_connection)
# print(hotfiles,hotfiles_details)
# os.makedirs('cBench_hotfiles', exist_ok=True)
# with open(f'./cBench_hotfiles/{args.benchmark}_hotfiles.json','w') as file:
#     json.dump(hotfiles_details, file, indent=4)
# assert 1==0

fun = Function_wrap(
                    build_cmd=build_cmd, #编译命令，用户提供
                    build_dir=build_dir, #编译路径，用户提供
                    tmp_dir=tmp_dir, #数据存放目录，用户定义
                    run_cmd=run_cmd, #运行命令，用户提供
                    run_dir=run_dir, #运行路径，用户提供
                    binary=binary, #编译后的二进制文件路径，用户提供
                    ssh_connection = ssh_connection, #ssh连接
                    )
fun.build('default<O3>') # 首先不考虑热点文件在O3下编译，确保非热点文件均在O3下已编译，防止后续编译出错
fun.hotfiles = hotfiles # 然后加入热点文件，此后函数每次接受新的编译配置时，只会编译热点文件

if __name__ == "__main__":
    if args.method=='random': 
        optimizer=random_optimizer(fun=fun, passes=passes, budget=args.budget)
        best_cfg, best_cost = optimizer.minimize()
        print('best runtime:', best_cost)

    if args.method=='random-single': 
        import pickle

        hotfile = hotfiles[0]
        new_tmp_dir = tmp_dir.replace(args.benchmark, f'{args.benchmark}_{hotfile}')
        print(tmp_dir)
        fun = Function_wrap(
                    build_cmd=build_cmd, #编译命令，用户提供
                    build_dir=build_dir, #编译路径，用户提供
                    tmp_dir=new_tmp_dir, #数据存放目录，用户定义
                    run_cmd=run_cmd, #运行命令，用户提供
                    run_dir=run_dir, #运行路径，用户提供
                    binary=binary, #编译后的二进制文件路径，用户提供
                    ssh_connection = ssh_connection, #ssh连接
                    max_n_measure = 3, #每个配置最多测量次数
                    )
        fun.build('default<O3>') # 首先不考虑热点文件在O3下编译，确保非热点文件均在O3下已编译，防止后续编译出错
        fun.hotfiles = [hotfile] # 然后加入热点文件，此后函数每次接受新的编译配置时，只会编译热点文件

        with open('obj.pickle', 'wb') as f:
            pickle.dump(fun, f)

        optimizer=random_optimizer(fun=fun, passes=passes, budget=args.budget)
        # print(fun.__dict__)
        serialized = pickle.dumps(fun)
        best_cfg, best_cost = optimizer.minimize()
        print('best runtime:', best_cost)

        # with open('obj.pickle', 'wb') as f:
        #     pickle.dump(fun, f)
        

        hotfile = hotfiles[0]
        new_tmp_dir = tmp_dir.replace(args.benchmark, f'{args.benchmark}_{hotfile}')
        # ssh_connection=Connection(host=f'nvidia@TX2-{args.device}.local') 
        fun2 = Function_wrap(
                    build_cmd=build_cmd, #编译命令，用户提供
                    build_dir=build_dir, #编译路径，用户提供
                    tmp_dir=new_tmp_dir, #数据存放目录，用户定义
                    run_cmd=run_cmd, #运行命令，用户提供
                    run_dir=run_dir, #运行路径，用户提供
                    binary=binary, #编译后的二进制文件路径，用户提供
                    ssh_connection = ssh_connection, #ssh连接
                    max_n_measure = 3, #每个配置最多测量次数
                    )
        fun2.build('default<O3>') # 首先不考虑热点文件在O3下编译，确保非热点文件均在O3下已编译，防止后续编译出错
        fun2.hotfiles = [hotfile] # 然后加入热点文件，此后函数每次接受新的编译配置时，只会编译热点文件
        for name in fun2.__dict__:
            print(name)
            attr_value = getattr(fun2, name)
            print(attr_value)
            serialized = pickle.dumps(attr_value)

        serialized = pickle.dumps(fun2)

        optimizer=random_optimizer(fun=fun, passes=passes, budget=args.budget)
        best_cfg, best_cost = optimizer.minimize()
        print('best runtime:', best_cost)

        for hotfile in hotfiles:
            new_tmp_dir = tmp_dir.replace(args.benchmark, f'{args.benchmark}_{hotfile}')
            print(tmp_dir)
            fun = Function_wrap(
                    build_cmd=build_cmd, #编译命令，用户提供
                    build_dir=build_dir, #编译路径，用户提供
                    tmp_dir=new_tmp_dir, #数据存放目录，用户定义
                    run_cmd=run_cmd, #运行命令，用户提供
                    run_dir=run_dir, #运行路径，用户提供
                    binary=binary, #编译后的二进制文件路径，用户提供
                    ssh_connection = ssh_connection, #ssh连接
                    max_n_measure = 3, #每个配置最多测量次数
                    )
            fun.build('default<O3>') # 首先不考虑热点文件在O3下编译，确保非热点文件均在O3下已编译，防止后续编译出错
            fun.hotfiles = [hotfile] # 然后加入热点文件，此后函数每次接受新的编译配置时，只会编译热点文件
            optimizer=random_optimizer(fun=fun, passes=passes, budget=args.budget)
            best_cfg, best_cost = optimizer.minimize()
            print('best runtime:', best_cost)

    if args.method=='nevergrad':
        optimizer=nevergrad_optimizer(fun=fun, passes=passes, budget=args.budget)
        best_cfg, best_cost = optimizer.minimize()
        print('best runtime:', best_cost)
    
    if args.method=='BO':
        # import pickle
        # pickle_bytes = pickle.dumps(fun.gen_optIR)
        # y = fun('default<O3>')
        # pickle_bytes = pickle.dumps(fun.aaa)
        # pickle_bytes = pickle.dumps(fun.static_gen_optIR)
        BO=BO(
                fun=fun,
                passes=passes, 
                budget=args.budget, 
                acqf='EI',
                n_init=3,
                max_cand_seqs = 1000,
                device=args.server,
                )
        BO.minimize()

    if args.method=='O3':
        y = fun('default<O3>')
        print('O3 runtime:', y)
    
    if args.method=='O2':
        y = fun('default<O2>')
        print('O2 runtime:', y)
    

    if args.method == 'test-gsm_longterm':
        from llvmtuner.searchspace import passlist2str, parse_O3string, split_by_parentheses
        from llvmtuner.feature_extraction import read_optstats_from_cfgjson
        fun.hotfiles=['long_term']
        # cfg_path ="/home/jiayu/result_llvmtuner_17_arm/cBench/telecom_gsm_long_term/random-single/LLVMTuner-cfg/cfg-f4372a95632ea040c8aa23338c2a4f2d.json"
        # with open(cfg_path, 'r') as file:
        #     best_params = json.load(file)['params']
        # fun(best_params)

        # reduced_params, y_ref = fun.reduce_pass(best_params)
        # print(reduced_params, y_ref)
        # # best_params = {'long_term': 'function<eager-inv>(sroa<preserve-cfg>,simplifycfg<bonus-inst-threshold=1;forward-switch-cond;switch-range-to-icmp;switch-to-lookup;no-keep-loops;hoist-common-insts;sink-common-insts;speculate-blocks;simplify-cond-branch>,loop-unroll<O3>,slp-vectorizer)'}

        # seq = parse_O3string(reduced_params['long_term'])
        # clear_reduced_seq = [split_by_parentheses(x)[-1].split('<')[0] for x in seq]
        # print(clear_reduced_seq)

        params={'long_term': 'function<eager-inv>(mem2reg,slp-vectorizer),cgscc(devirt<4>(function<eager-inv;no-rerun>(loop-mssa(loop-rotate<header-duplication;no-prepare-for-lto>),simplifycfg<bonus-inst-threshold=1;no-forward-switch-cond;switch-range-to-icmp;no-switch-to-lookup;keep-loops;hoist-common-insts;sink-common-insts;speculate-blocks;simplify-cond-branch>,instcombine<max-iterations=1000;no-use-loop-info>))),function<eager-inv>(loop-vectorize<no-interleave-forced-only;no-vectorize-forced-only;>,loop-unroll<O3>,instcombine<max-iterations=1000;no-use-loop-info>),cgscc(devirt<4>(function<eager-inv;no-rerun>(sroa<modify-cfg>)))'}
        fun(params)
        seq = parse_O3string(params['long_term'])
        clear_seq = [split_by_parentheses(x)[-1].split('<')[0] for x in seq]
        dict1 = dict(zip(clear_seq, seq))
        seq = ['mem2reg', 'slp-vectorizer', 'loop-rotate', 'simplifycfg', 'instcombine', 'loop-vectorize', 'loop-unroll', 'instcombine', 'sroa']
        seq = ['mem2reg', 'slp-vectorizer']
        seq = [dict1[x] for x in seq]
        params['long_term'] = passlist2str(seq)
        fun(params)
        cfg0={}
        cfg0['params']=params 
        cfg0['tmp_dir']=fun.tmp_dir
        cfg_json0=json.dumps(cfg0)
        features0 = read_optstats_from_cfgjson(cfg_json0)
        print(json.dumps(features0,indent=2))
        # reduced_params, y_ref = fun.reduce_pass(params)
    
    if args.method == 'test-best':
        from llvmtuner.searchspace import passlist2str, parse_O3string, split_by_parentheses
        from llvmtuner.feature_extraction import read_optstats_from_cfgjson
        fun.hotfiles=['adpcm']
       
        # result_dir = '/home/jiayu/result_llvmtuner_17_arm/cBench/telecom_adpcm_c/BO/result.json'
        # best_time = inf
        # with open(result_dir, 'rb') as file:
        #     for line in file:
        #         config_path, time = json.loads(line)
        #         if time < best_time:
        #             best_time = time
        #             best_config_path = config_path
        # with open(best_config_path, 'r') as file:
        #     config = json.load(file)
        #     params=config['params']
        # fun(params)

        params={'adpcm': 'function<eager-inv>(sroa<modify-cfg>,early-cse<>),globalopt,cgscc(devirt<4>(function<eager-inv;no-rerun>(jump-threading,simplifycfg<bonus-inst-threshold=1;no-forward-switch-cond;switch-range-to-icmp;no-switch-to-lookup;keep-loops;hoist-common-insts;sink-common-insts;speculate-blocks;simplify-cond-branch>))),function<eager-inv>(instcombine<max-iterations=1000;no-use-loop-info>),cgscc(devirt<4>(function<eager-inv;no-rerun>(reassociate)))'}
        fun(params)
        cfg0={}
        cfg0['params']=params 
        cfg0['tmp_dir']=fun.tmp_dir
        cfg_json0=json.dumps(cfg0)
        features0 = read_optstats_from_cfgjson(cfg_json0)
        print(json.dumps(features0,indent=2))

        seq = parse_O3string(params['adpcm'])
        clear_seq = [split_by_parentheses(x)[-1].split('<')[0] for x in seq]
        dict1 = dict(zip(clear_seq, seq))

        seq = ['sroa', 'early-cse', 'globalopt', 'jump-threading', 'simplifycfg', 'instcombine', 'reassociate']
        seq = ['sroa', 'jump-threading', 'early-cse', 'globalopt', 'simplifycfg', 'instcombine', 'reassociate']
        seq = [dict1[x] for x in seq]
        params['adpcm'] = passlist2str(seq)
        fun(params)
        

        # reduced_params, y_ref = fun.reduce_pass(params)
        # print(reduced_params, y_ref)
        # seq = parse_O3string(reduced_params['adpcm'])
        # clear_reduced_seq = [split_by_parentheses(x)[-1].split('<')[0] for x in seq]
        # print(clear_reduced_seq)

        cfg0={}
        cfg0['params']=params 
        cfg0['tmp_dir']=fun.tmp_dir
        cfg_json0=json.dumps(cfg0)
        features0 = read_optstats_from_cfgjson(cfg_json0)
        print(json.dumps(features0,indent=2))
    


    if args.method=='reduce':
        from llvmtuner.searchspace import passlist2str, parse_O3string, split_by_parentheses
        from llvmtuner.feature_extraction import read_optstats_from_cfgjson
        # result_dir = '/home/jiayu/result_llvmtuner_17/cBench/security_sha/cost_model/result.json'
        # tmp_dir = '/home/jiayu/result_llvmtuner_17/cBench/security_sha/cost_model/'
        fileroot = 'sha'
        # with open(result_dir, 'r') as file:
        #     for line in file:
        #         config_path, time = json.loads(line)
        # print(config_path, time)
        # with open(config_path, 'r') as file:
        #     config = json.load(file)
        #     params=config['params']
        # y = fun('default<O3>')
        params = {'sha': 'cgscc(devirt<4>(function<eager-inv;no-rerun>(early-cse<memssa>,loop-mssa(loop-rotate<header-duplication;no-prepare-for-lto>),instcombine<max-iterations=1000;no-use-loop-info>))),function<eager-inv>(loop-fusion),cgscc(devirt<4>(function<eager-inv;no-rerun>(gvn<>))),function<eager-inv>(slp-vectorizer),cgscc(devirt<4>(function<eager-inv;no-rerun>(instcombine<max-iterations=1000;no-use-loop-info>))),ipsccp,function<eager-inv>(loop-unroll<O3>)'}
        seq = parse_O3string(params['sha'])
        # print(seq)
        seq0 = ['cgscc(devirt<4>(function<eager-inv;no-rerun>(early-cse<memssa>)))', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(instcombine<max-iterations=1000;no-use-loop-info>)))', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(loop-mssa(loop-rotate<header-duplication;no-prepare-for-lto>))))', 'function<eager-inv>(loop-fusion)', 'sroa', 'function<eager-inv>(loop-unroll<O3>)']

        seq0_remove = ['cgscc(devirt<4>(function<eager-inv;no-rerun>(early-cse<memssa>)))', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(instcombine<max-iterations=1000;no-use-loop-info>)))', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(loop-mssa(loop-rotate<header-duplication;no-prepare-for-lto>))))', 'function<eager-inv>(loop-unroll<O3>)','sroa']
        seq1 =  ['cgscc(devirt<4>(function<eager-inv;no-rerun>(early-cse<memssa>)))', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(loop-mssa(loop-rotate<header-duplication;no-prepare-for-lto>))))','function<eager-inv>(loop-fusion)', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(instcombine<max-iterations=1000;no-use-loop-info>)))']
        seq1_remove = ['cgscc(devirt<4>(function<eager-inv;no-rerun>(early-cse<memssa>)))', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(loop-mssa(loop-rotate<header-duplication;no-prepare-for-lto>))))', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(instcombine<max-iterations=1000;no-use-loop-info>)))']
        

        seq2 = ['cgscc(devirt<4>(function<eager-inv;no-rerun>(early-cse<memssa>)))', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(loop-mssa(loop-rotate<header-duplication;no-prepare-for-lto>))))', 'function<eager-inv>(loop-fusion)', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(instcombine<max-iterations=1000;no-use-loop-info>)))', 'sroa', 'function<eager-inv>(loop-unroll<O3>)']
        seq3 = ['cgscc(devirt<4>(function<eager-inv;no-rerun>(instcombine<max-iterations=1000;no-use-loop-info>)))', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(early-cse<memssa>)))', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(loop-mssa(loop-rotate<header-duplication;no-prepare-for-lto>))))', 'sroa','function<eager-inv>(loop-fusion)', 'function<eager-inv>(loop-unroll<O3>)']

        seq =seq0
        seq_reomve = seq0_remove
        clear_seq = [split_by_parentheses(x)[-1].split('<')[0] for x in seq]
        print(' '.join(clear_seq))
        clear_seq = [split_by_parentheses(x)[-1].split('<')[0] for x in seq_reomve]
        print(' '.join(clear_seq))
        params['sha'] = passlist2str(seq)
        y = fun(params)
        assert 1==0
        
        cfg0={}
        cfg0['params']=params 
        cfg0['tmp_dir']=fun.tmp_dir
        cfg_json0=json.dumps(cfg0)
        features0 = read_optstats_from_cfgjson(cfg_json0)
        features0 = {k[4:]:v for k,v in features0.items()}
        print(json.dumps(features0,indent=2))
        print('speedup', 0.345/y)

        params['sha'] = passlist2str(seq_reomve)
        y = fun(params)
        cfg0={}
        cfg0['params']=params 
        cfg0['tmp_dir']=fun.tmp_dir
        cfg_json0=json.dumps(cfg0)
        features0 = read_optstats_from_cfgjson(cfg_json0)
        features0 = {k[4:]:v for k,v in features0.items()}
        print(json.dumps(features0,indent=2))
        print('speedup', 0.39/y)

        IR = os.path.join(fun.tmp_dir, fileroot, 'IR-{}/'.format( hashlib.md5(passlist2str(seq).encode('utf-8')).hexdigest()), 'sha.opt.bc')
        IR1 = os.path.join(fun.tmp_dir, fileroot, 'IR-{}/'.format( hashlib.md5(passlist2str(seq_reomve).encode('utf-8')).hexdigest()), 'sha.opt.bc')
        subprocess.run(f'diff {IR} {IR1}', shell=True)
        

        
        

        


        # reduced_params, y_ref = fun.reduce_pass(params)
        # print(reduced_params, y_ref)



    
    

    

        
    
        
                    
            
        
        
        
        
        
        
   
    
   
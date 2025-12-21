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
import shutil




import llvmtuner
from llvmtuner.searchspace import default_space, passlist2str, parse_O3string
from llvmtuner.feature_extraction import read_optstats_from_cfgpathlist,read_optstats_from_cfgjsonlist,stats2vec
from llvmtuner.BO.BO import BO
from llvmtuner.BO.Adalocaloptimizer import Adalocaloptimizer
from llvmtuner.BO.Localoptimizer import Localoptimizer
from llvmtuner.function_wrap import Function_wrap
from llvmtuner.gen_hotfiles import perf_record, gen_hotfiles, gprof_record_ssh, parse_gprof_report, hotfunctions2hotfiles,obtain_commands_in_sh
from llvmtuner.show_features import read_json_lines


parser = argparse.ArgumentParser()
parser.add_argument('--method', required=True, help='')
parser.add_argument('--benchmark', required=True, help='')
parser.add_argument('--budget', type=int, default=300, help='')
parser.add_argument('--server', default='cpu', help='')
# parser.add_argument('--node', required=True, help='')
args = parser.parse_args()

passes=llvmtuner.searchspace.default_space()[0]

other = ['502.gcc_r','531.deepsjeng_r','557.xz_r','525.x264_r'] 
test=['505.mcf_r','520.omnetpp_r', '541.leela_r','544.nab_r']
train=['510.parest_r','511.povray_r','519.lbm_r']
different = ['523.xalancbmk_r','526.blender_r']
analyze = ['538.imagick_r','508.namd_r','500.perlbench_r']

all_benchmarks = other + test + train + different + analyze
host="jiayu@dss4090.local"
sshC=Connection(host=host)

if args.benchmark == '511.povray_r':
    extra_flag = 'TARGET=povray_r'
elif args.benchmark == '538.imagick_r':
    extra_flag = 'TARGET=imagick_r'
elif args.benchmark == '526.blender_r':
    extra_flag = 'TARGET=blender_r'
elif args.benchmark == '525.x264_r':
    extra_flag = 'TARGET=x264_r'
else:
    extra_flag = ''

if args.benchmark in ['525.x264_r']:
    build_cmd = f'specmake {extra_flag} SPECLANG="clangopt -fcommon" -j20'
else:
    build_cmd = f'specmake {extra_flag} SPECLANG=clangopt SPECLANGXX=clangxxopt -j20'

build_dir = f'/home/jiayu/cpu2017/benchspec/CPU/{args.benchmark}/build/build_base_llvmtuner17.0.6.0000/'
tmp_dir = os.path.join(os.path.expanduser('~/result_llvmtuner_17_x86/SPEC/'), args.benchmark, args.method)
run_dir = f'/home/jiayu/spec2017_run/{args.benchmark}'
run_cmd = f'./run_{args.benchmark}.sh'

if args.benchmark == '502.gcc_r':
    binary_name = 'cpugcc_r'
elif args.benchmark == '523.xalancbmk_r':
    binary_name = 'cpuxalan_r'
else:
    binary_name = args.benchmark.split('.')[1]

binary = os.path.join(build_dir, binary_name)

with open(f'{args.benchmark}_hotfiles.json','r') as file:
    hotfiles_details = json.load(file)
hotfiles = hotfiles_details[0]


node2ben = {'1':['500.perlbench_r','502.gcc_r','505.mcf_r','508.namd_r','510.parest_r','511.povray_r','519.lbm_r'], '2':['520.omnetpp_r','523.xalancbmk_r','525.x264_r','526.blender_r'], '3':['531.deepsjeng_r','538.imagick_r','541.leela_r','544.nab_r','557.xz_r']}

if args.benchmark in node2ben['1']:
    node = 1
    cpu = 16
    L3_cache = '0x00f0'
elif args.benchmark in node2ben['2']:
    node = 2
    cpu = 32
    L3_cache = '0x0f00'
else:
    node = 3
    cpu = 48
    L3_cache = '0xf000'

ben2O3time = {'500.perlbench_r': 25.06, '502.gcc_r': 47.31, '505.mcf_r': 12.19, '508.namd_r': 34.2, '510.parest_r': 34.25, '511.povray_r': 4.49, '519.lbm_r': 21.13, '520.omnetpp_r': 4.28, '523.xalancbmk_r': 61.4, '525.x264_r': 22.48, '526.blender_r': 141.96, '531.deepsjeng_r': 72.1, '538.imagick_r': 25.1, '541.leela_r': 5.7, '544.nab_r': 1.23, '557.xz_r': 42.72}
largest_time = 2 + 1.5*ben2O3time[args.benchmark] if args.benchmark in ben2O3time else 500
run_cmd = f'time sudo cgexec -g cpuset:mygroup rdtset -t "l3={L3_cache};mba=100;cpu={cpu},{cpu+64}" -c {cpu},{cpu+64} -k numactl --membind={node} timeout {largest_time} ./run_{args.benchmark}.sh'
print(run_cmd)


def run_and_eval_fun():
    run_dir = f'/home/jiayu/spec2017_run/{args.benchmark}'
    try:
        ret = sshC.put(local=os.path.join(build_dir, binary_name), remote=run_dir)
    except Exception as e:
        try:
            time.sleep(1)
            ret = sshC.put(local=os.path.join(build_dir, binary_name), remote=run_dir)
        except Exception as e:
            try:
                time.sleep(1)
                ret = sshC.put(local=os.path.join(build_dir, binary_name), remote=run_dir)
            except Exception as e:
                assert 1==0, os.path.join(build_dir, binary_name)

    try:
        with sshC.cd(run_dir):
            ret=sshC.run(run_cmd, hide=True, timeout=500)
        temp=ret.stderr.strip()
        real=temp.split('\n')[-3]
        searchObj = re.search( r'real\s*(.*)m(.*)s.*', real)
        runtime = int(searchObj[1])*60+float(searchObj[2])
    except Exception as e:
        runtime = largest_time
    return runtime 

def run_multicmds_gprof(multi_run_cmds):
    run_dir = f'/home/jiayu/spec2017_run/{args.benchmark}'
    try:
        ret = sshC.put(local=os.path.join(build_dir, binary_name), remote=run_dir)
    except Exception as e:
        try:
            time.sleep(1)
            ret = sshC.put(local=os.path.join(build_dir, binary_name), remote=run_dir)
        except Exception as e:
            try:
                time.sleep(1)
                ret = sshC.put(local=os.path.join(build_dir, binary_name), remote=run_dir)
            except Exception as e:
                assert 1==0, os.path.join(build_dir, binary_name)

    try:
        with sshC.cd(run_dir):
            i=0
            files_list = []
            for single_run_cmd in multi_run_cmds:
                ret=sshC.run(single_run_cmd, hide=True, timeout=500)
                sshC.run(f'mv gmon.out gmon{i}.out')
                files_list.append(f'gmon{i}.out')
                i+=1
            files = ' '.join(files_list)
            sshC.run(f'gprof -s {binary_name} {files}')
            sshC.run(f'mv gmon.sum gmon.out')
    except Exception as e:
        assert 1==0
    return 

fun = Function_wrap(
    build_cmd = build_cmd, 
    build_dir = build_dir, 
    tmp_dir = tmp_dir, 
    run_cmd = run_cmd, 
    run_dir = run_dir,  
    run_and_eval_fun = run_and_eval_fun
    )
fun.repeat = 1
fun.adaptive_measure = False
fun.hotfiles = hotfiles

# t0=time.time()
# print('-----------------build -O3-----------------')
# fun.build('default<O3>')
# print('O3 compilation time:',time.time()-t0)

len_seq=120

if args.method == 'O3':
    # subprocess.run(f'specmake {extra_flag} clean', cwd=build_dir, shell=True)
    y = fun('default<O3>')

if args.method == 'random':
    subprocess.run(f'specmake {extra_flag} clean', cwd=build_dir, shell=True)
    from llvmtuner.baselines.random import random_optimizer
    optimizer=random_optimizer(fun=fun, passes=passes, budget=args.budget)
    best_cfg, best_cost = optimizer.minimize()
    print('best runtime:', best_cost)

if args.method=='nevergrad':
    subprocess.run(f'specmake {extra_flag} clean', cwd=build_dir, shell=True)
    from llvmtuner.baselines.nevergrad import nevergrad_optimizer
    optimizer=nevergrad_optimizer(fun=fun, passes=passes, budget=args.budget)
    best_cfg, best_cost = optimizer.minimize()
    print('best runtime:', best_cost)

if args.method=='BO':
    subprocess.run(f'specmake {extra_flag} clean', cwd=build_dir, shell=True)
    from llvmtuner.BO.BO import BO
    # print(fun.hotfiles)
    # fun.build('default<O3>')
    BO=BO(
            fun=fun,
            passes=passes, 
            budget=args.budget, 
            acqf='EI',
            n_init=20,
            max_cand_seqs = 5000,
            device=args.server,
            )
    BO.minimize()

if args.method=='clear':
    subprocess.run(f'specmake {extra_flag} clean', cwd=build_dir, shell=True)

if args.method == 'test-best':
    from llvmtuner.searchspace import passlist2str, parse_O3string, split_by_parentheses
    from llvmtuner.feature_extraction import read_optstats_from_cfgjson
    fileroot = hotfiles[0]
    fun.hotfiles = [fileroot]
    
    # result_dir = f'/home/jiayu/result_llvmtuner_17_x86/SPEC/{args.benchmark}/BO/result.json'
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
    
    result_dir = f'/home/jiayu/result_llvmtuner_17_x86/SPEC/{args.benchmark}/random/best_result100.json'
    with open(result_dir, 'rb') as file:
        data = json.load(file)
        params = data[0]
    fun(params)

    reduced_params, y_ref = fun.reduce_pass(params)
    print(reduced_params, y_ref)
    seq = parse_O3string(reduced_params[fileroot])
    clear_reduced_seq = [split_by_parentheses(x)[-1].split('<')[0] for x in seq]
    print(clear_reduced_seq)
    params = reduced_params
    
    fun(params)
    cfg0={}
    cfg0['params'] = params 
    cfg0['tmp_dir']=fun.tmp_dir
    cfg_json0=json.dumps(cfg0)
    features0 = read_optstats_from_cfgjson(cfg_json0)
    print(json.dumps(features0,indent=2))

if args.method == 'gprof':
    subprocess.run(f'specmake {extra_flag} clean', cwd=build_dir, shell=True)
    if args.benchmark in ['525.x264_r']:
        fun.build_cmd = f'specmake {extra_flag} SPECLANG="clangopt -pg -fcommon" -j20'
    else:
        fun.build_cmd = f'specmake {extra_flag} SPECLANG="clangopt -pg" SPECLANGXX="clangxxopt -pg" -j20' 
    
    run_commands = obtain_commands_in_sh(os.path.join('/home/jiayu/spec2017_run/', args.benchmark, f'run_{args.benchmark}.sh'))
    n_commands =len(run_commands)
    print('Num of commands', args.benchmark, n_commands)

    subprocess.run(f'specmake {extra_flag} clean', cwd=build_dir, shell=True)
    module2funcnames = fun._get_func_names()

    if n_commands>1:
        fun.build('default<O3>') 
        run_multicmds_gprof(run_commands)
    else:
        pass
        y = fun('default<O3>')

    gprof_record_file = gprof_record_ssh(sshC, binary, run_dir)
    print(gprof_record_file)

    if args.benchmark in test:
        suffix = '_test'
    else:
        suffix = '_train'
    directory, filename = os.path.split(gprof_record_file)
    basename, ext = os.path.splitext(filename)
    new_filename = f"{basename}{suffix}{ext}"
    new_file_path = os.path.join(directory, new_filename)
    shutil.copy(gprof_record_file, new_file_path)

    function_times = parse_gprof_report(gprof_record_file)
    # print('='*10)
    # for module in module2funcnames:
    #     print(module)
    #     print(module2funcnames[module])
    # print('='*10)
    # print(function_times)
    print(np.sum(list(function_times.values())))
    # print('='*10)
    hotfiles, hotfiles_details, module2cost = hotfunctions2hotfiles(module2funcnames, function_times, threshold=0.95)
    print(hotfiles)
    # print(hotfiles_details)
    print(module2cost)
    print(np.sum(list(module2cost.values())))

    with open(f'{args.benchmark}_hotfiles.json','w') as file:
        json.dump([hotfiles, hotfiles_details, module2cost], file, indent=4)






if args.method == 'perf':
    module2funcnames = fun._get_func_names()
    print(module2funcnames)
    # fun('default<O3>')#
    folded_perf_result = perf_record(sshC, build_dir, run_dir, run_cmd)
    print(folded_perf_result)
    hotfiles,hotfiles_details = gen_hotfiles(module2funcnames, binary, folded_perf_result)
    print(hotfiles, hotfiles_details)
    with open(f'{args.benchmark}_hotfiles.json','w') as file:
        json.dump(hotfiles_details, file, indent=4)


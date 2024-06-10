# -*- coding: utf-8 -*-
import os
import argparse
from fabric import Connection
import subprocess
import time


def create_shell_script(script_name, commands):
    # 添加 shebang
    content = "#!/bin/bash\n\n"
    
    # 添加命令
    content += '\n'.join(commands)
    
    # 写入文件
    with open(script_name, 'w') as f:
        f.write(content)
    
    # 修改权限使其可执行
    os.chmod(script_name, 0o755)



def run_command_with_timing(command, cwd =None):
    # 开始计时
    start_time = time.time()

    # 使用subprocess运行命令
    result = subprocess.run(command, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # 停止计时
    end_time = time.time()

    # 计算运行时间
    elapsed_time = end_time - start_time
    if result.returncode == 0:
        # 返回运行结果、错误信息和运行时间
        return result.stdout, result.stderr, elapsed_time
    else:
        return result.stdout, result.stderr, 0.0


def find_latest_folder(directory):
    try:
        # 获取目录下的所有子目录
        subdirectories = [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))]
        
        # 按照修改时间排序子目录
        subdirectories.sort(key=lambda x: os.path.getmtime(os.path.join(directory, x)), reverse=True)
        
        # 返回最新的子目录的完整路径
        latest_folder = subdirectories[0] if subdirectories else None
        return os.path.join(directory, latest_folder) if latest_folder else None

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None



# other = ['502.gcc_r','525.x264_r','531.deepsjeng_r','557.xz_r']
# test=['505.mcf_r','520.omnetpp_r', '541.leela_r','544.nab_r']
# train=['510.parest_r','511.povray_r','519.lbm_r']
# different = ['523.xalancbmk_r','526.blender_r']
# analyze = ['538.imagick_r','508.namd_r','500.perlbench_r']


benchmarks = ['500.perlbench_r', '502.gcc_r', '505.mcf_r', '508.namd_r', '510.parest_r', '511.povray_r', '519.lbm_r', '520.omnetpp_r', '523.xalancbmk_r', '525.x264_r', '526.blender_r', '531.deepsjeng_r', '538.imagick_r', '541.leela_r', '544.nab_r', '557.xz_r']


for benchmark in benchmarks:
    print(benchmark)
    run_dir = os.path.expanduser(f'~/spec2017_run/{benchmark}')
    subprocess.run(f'rm -rf {run_dir}', shell=True)
    subprocess.run(f'mkdir -p {run_dir}', shell=True)

    workload = 'train'
    # cmd = f'runcpu --action runsetup --loose --size {workload} --config my-clang-linux-cross_x862aarch64.cfg {benchmark}'
    cmd = f'runcpu --action runsetup --loose --size {workload} --config my-clang-linux-x86.cfg {benchmark}'
    stdout, stderr, elapsed_time = run_command_with_timing(cmd)
    assert elapsed_time!=0, benchmark
    
    
    cmd = f'specinvoke -n'
    cwd = find_latest_folder(os.path.expanduser(f'~/cpu2017/benchspec/CPU/{benchmark}/run'))
    dir_name = os.path.split(cwd)[-1]
    stdout, stderr, elapsed_time = run_command_with_timing(cmd, cwd)
    assert elapsed_time!=0
    myscript = f'run_{benchmark}.sh'
    print(stdout)
    create_shell_script(os.path.join(run_dir, myscript), stdout.replace(f'../{dir_name}','.').splitlines()[:-1])

    cmd = f'spectar cf - {dir_name}/ | specxz > myrun.tar.xz'
    stdout, stderr, elapsed_time = run_command_with_timing(cmd, os.path.expanduser(f'~/cpu2017/benchspec/CPU/{benchmark}/run'))
    assert elapsed_time!=0
    
    local=os.path.join(f'~/cpu2017/benchspec/CPU/{benchmark}/run', 'myrun.tar.xz')
    subprocess.run(f'cp {local} {run_dir}',shell=True)
    cmd = f'xz -dc myrun.tar.xz | tar -xvf - --strip-components=1'#
    subprocess.run(cmd, cwd=run_dir, shell=True)

    
    
    

    



    




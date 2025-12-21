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



other = ['502.gcc_r','525.x264_r','531.deepsjeng_r','557.xz_r']
test=['505.mcf_r','520.omnetpp_r', '541.leela_r','544.nab_r']
train=['510.parest_r','511.povray_r','519.lbm_r']
different = ['523.xalancbmk_r','526.blender_r']
analyze = ['538.imagick_r','508.namd_r','500.perlbench_r']

benchmarks = other + test + train + different + analyze
# benchmarks = ['500.perlbench_r', '502.gcc_r', '505.mcf_r', '508.namd_r', '510.parest_r', '511.povray_r', '519.lbm_r', '520.omnetpp_r', '523.xalancbmk_r', '525.x264_r', '526.blender_r', '531.deepsjeng_r', '538.imagick_r', '541.leela_r', '544.nab_r', '557.xz_r']


host="jiayu@dss4090.local"
sshC=Connection(host=host)
# with sshC.cd(f'/home/jiayu/spec2017_run/'):  
#     sshC.run('rm -r -f *', hide=True, timeout=100)


# benchmarks = ['525.x264_r']
benchmarks = ['526.blender_r']
for benchmark in benchmarks:
    # if benchmark == '525.x264_r':
    #     continue
    print(benchmark)
    if benchmark in test:
        workload = 'test'
    else:
        workload = 'train'
    run_dir = os.path.expanduser(f'~/spec2017_run/{benchmark}')
    subprocess.run(f'rm -rf {run_dir}', shell=True)
    subprocess.run(f'mkdir -p {run_dir}', shell=True)
    
    # cmd = f'runcpu --action runsetup --loose --size {workload} --config my-clang-linux-cross_x862aarch64.cfg {benchmark}'
    if benchmark == '525.x264_r':
        cmd = f'runcpu --action runsetup --loose --size {workload} --config my-clang-linux-x86.cfg --define clangflag="-fcommon" {benchmark}'
    else:
        cmd = f'runcpu --action runsetup --loose --size {workload} --config my-clang-linux-x86.cfg {benchmark}'
    stdout, stderr, elapsed_time = run_command_with_timing(cmd)
    assert elapsed_time!=0, [benchmark,cmd]
    
    
    cmd = f'specinvoke -n'
    cwd = find_latest_folder(os.path.expanduser(f'~/cpu2017/benchspec/CPU/{benchmark}/run'))
    dir_name = os.path.split(cwd)[-1]
    stdout, stderr, elapsed_time = run_command_with_timing(cmd, cwd)
    assert elapsed_time!=0
    myscript = f'run_{benchmark}.sh'
    print(stdout)
    create_shell_script(os.path.join(run_dir, myscript), stdout.replace(f'../{dir_name}','.').replace("_base.llvmtuner17.0.6", "").splitlines()[:-1])
    
    cmd = f'spectar cf - {dir_name}/ | specxz > myrun.tar.xz'
    stdout, stderr, elapsed_time = run_command_with_timing(cmd, os.path.expanduser(f'~/cpu2017/benchspec/CPU/{benchmark}/run'))
    assert elapsed_time!=0
    
    local=os.path.join(f'~/cpu2017/benchspec/CPU/{benchmark}/run', 'myrun.tar.xz')
    subprocess.run(f'cp {local} {run_dir}',shell=True)
    cmd = f'xz -dc myrun.tar.xz | tar -xvf - --strip-components=1'#
    subprocess.run(cmd, cwd=run_dir, shell=True)
    
    try:
        with sshC.cd(f'/home/jiayu/spec2017_run/'): #remote path
            sshC.run(f'mkdir -p {benchmark}')
        ret = sshC.put(local=os.path.expanduser(local), remote=run_dir) # remote holds the same path as local
        ret = sshC.put(local=os.path.join(run_dir, myscript), remote=run_dir) # remote holds the same path as local
    except Exception as e:
        assert 1==0

    try:
        with sshC.cd(run_dir):
            sshC.run(cmd, timeout=200)
    except Exception as e:
        assert 1==0

    
    
    

    



    




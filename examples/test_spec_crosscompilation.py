# -*- coding: utf-8 -*-
import os
import argparse
from fabric import Connection
import subprocess
import time

# parser = argparse.ArgumentParser()
# parser.add_argument('--device', required=True, help='')
# parser.add_argument('--method', required=True, help='')
# parser.add_argument('--benchmark', required=True, help='')
# parser.add_argument('--budget', type=int,default=50, help='')
# parser.add_argument('--n-parallel', type=int,default=50, help='')
# parser.add_argument('--batch-size', type=int, default=1)
# args = parser.parse_args()

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

# benchmarks = ['505.mcf_r', '520.omnetpp_r', '523.xalancbmk_r', '525.x264_r', '531.deepsjeng_r', '541.leela_r', '557.xz_r', '508.namd_r', '510.parest_r', '511.povray_r', '519.lbm_r', '538.imagick_r', '544.nab_r']

# some binaries of 525.x264_r require x86 compilation
# benchmarks = ['505.mcf_r', '520.omnetpp_r', '523.xalancbmk_r', '531.deepsjeng_r', '541.leela_r', '557.xz_r', '508.namd_r', '510.parest_r', '511.povray_r', '519.lbm_r', '538.imagick_r', '544.nab_r']

benchmarks = ['500.perlbench_r', '502.gcc_r', '505.mcf_r', '508.namd_r', '510.parest_r', '511.povray_r', '519.lbm_r', '520.omnetpp_r', '523.xalancbmk_r', '525.x264_r', '526.blender_r', '531.deepsjeng_r', '538.imagick_r', '541.leela_r', '544.nab_r', '557.xz_r']
# benchmarks = ['505.mcf_r', '520.omnetpp_r', '523.xalancbmk_r']
# benchmarks = ['538.imagick_r']
for benchmark in benchmarks:
    print(benchmark)
    if benchmark in test:
        workload = 'test'
    elif benchmark in train:
        workload = 'train'
    else:
        continue
    # cmd = f'runcpu --action runsetup --loose --size {workload} --config my-clang-linux-cross_x862aarch64.cfg {benchmark}'
    cmd = f'runcpu --action runsetup --loose --size {workload} --config my-clang-linux-x86.cfg {benchmark}'
    stdout, stderr, elapsed_time = run_command_with_timing(cmd)
    assert elapsed_time!=0, benchmark
    
    cmd = f'specinvoke -n'
    cwd = find_latest_folder(f'/home/jiayu/cpu2017/benchspec/CPU/{benchmark}/run')
    dir_name = os.path.split(cwd)[-1]
    stdout, stderr, elapsed_time = run_command_with_timing(cmd, cwd)
    assert elapsed_time!=0
    myscript = f'run_{benchmark}.sh'
    print(stdout)
    create_shell_script(myscript, stdout.replace(f'../{dir_name}','.').splitlines()[:-1])
    
    
    cmd = f'spectar cf - {dir_name}/ | specxz > myrun.tar.xz'
    stdout, stderr, elapsed_time = run_command_with_timing(cmd, f'/home/jiayu/cpu2017/benchspec/CPU/{benchmark}/run')
    assert elapsed_time!=0
    
    host="jiayu@dss4090.local"
    sshC=Connection(host=host)
    remote_dir = f'/home/jiayu/spec2017_run/{benchmark}'
    sshC.run(f'rm -rf {remote_dir}')
    sshC.run(f'mkdir -p {remote_dir}')
    result = sshC.put(local=os.path.join(f'/home/jiayu/cpu2017/benchspec/CPU/{benchmark}/run', 'myrun.tar.xz'), remote=remote_dir)
    cmd = f'xz -dc myrun.tar.xz | tar -xvf - --strip-components=1'# 
    with sshC.cd(remote_dir):
        ret=sshC.run(cmd, hide=True, timeout=100)
        assert not ret.failed
    
    result = sshC.put(local=myscript, remote=remote_dir)

    # for device in [1,2,3,4,5,6]:
    #     host="nvidia@TX2-{}.local".format(device)
    #     sshC=Connection(host=host)
    #     remote_dir = f'/home/nvidia/spec2017_run/{benchmark}'
    #     sshC.run(f'rm -rf {remote_dir}')
    #     sshC.run(f'mkdir -p {remote_dir}')
    #     result = sshC.put(local=os.path.join(f'/home/jiayu/cpu2017/benchspec/CPU/{benchmark}/run', 'myrun.tar.xz'), remote=remote_dir)
    #     cmd = f'xz -dc myrun.tar.xz | tar -xvf - --strip-components=1'# 
    #     with sshC.cd(remote_dir):
    #         ret=sshC.run(cmd, hide=True, timeout=100)
    #         assert not ret.failed

    #     result = sshC.put(local=myscript, remote=remote_dir)
        
        
        
        


# def modify_line(filename, line_number, text):
#     """
#     Modifies a specific line in a file.

#     :param filename: The name of the file to be modified.
#     :param line_number: The line number to modify (1-based index).
#     :param text: The new text that will replace the old line.
#     """
#     # Read the file and store the lines in a list
#     with open(filename, 'r') as file:
#         lines = file.readlines()

#     # Modify the specific line
#     if 0 < line_number <= len(lines):
#         lines[line_number - 1] = text + '\n'
#     else:
#         raise IndexError("Line number out of range.")

#     # Write the modified content back to the file
#     with open(filename, 'w') as file:
#         file.writelines(lines)

# Example usage:
# modify_line(f'/home/jiayu/cpu2017/benchspec/CPU/520.omnetpp_r/run/{dir_name}/omnetpp.ini', 3, 'sim-time-limit = 0.03s')




    
    # cmd = f'runcpu --action build --make_no_clobber --loose --size train --config my-clang-linux-cross_x862aarch64.cfg {benchmark}'


# host="nvidia@TX2-{}.local".format(args.device)
# sshC=Connection(host=host)
# def run_and_eval_fun():
#     run_dir = '/home/nvidia/cBench_V1.1/{}/src_work/'.format(args.benchmark)
#     result = sshC.put(local=os.path.join(ben_dir,'a.out'), remote=run_dir)
#     if result.failed:
#         raise ValueError("scp failed")
    
#     run_cmd = './__run 1 {}'.format(ben2num[args.benchmark])
#     try:
#         with sshC.cd(run_dir):
#             ret=sshC.run(run_cmd, hide=True, timeout=100)
#         temp=ret.stderr.strip()
#         real=temp.split('\n')[-3]
#         searchObj = re.search( r'real\s*(.*)m(.*)s.*', real)
#         runtime = int(searchObj[1])*60+float(searchObj[2])
#     except invoke.exceptions.UnexpectedExit:
#         runtime = inf
#     except invoke.exceptions.CommandTimedOut:
#         runtime = inf
#     return runtime 




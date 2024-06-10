import numpy as np
import time
import subprocess
import os
import hashlib
import json
import shutil
from multiprocessing import Pool
import llvmtuner
from llvmtuner.function_wrap import Function_wrap

def perf_record(binary, run_dir, run_cmd):
    #如果编译后的binary不在运行目录，复制文件到运行目录
    binary_dir = os.path.dirname(binary)
    if not os.path.samefile(binary_dir, run_dir):
        shutil.copy(binary, run_dir)

    cmd = f"sudo perf record -F 999 -b -g -- {run_cmd}"
    ret = subprocess.run(cmd, shell=True, cwd = run_dir)
    assert ret.returncode == 0, cmd

    cmd = f"sudo perf script > out.perf"
    ret = subprocess.run(cmd, shell=True, cwd = run_dir)
    assert ret.returncode == 0, cmd

    cmd = f"~/FlameGraph/stackcollapse-perf.pl out.perf > out.folded"
    ret = subprocess.run(cmd, shell=True, cwd = run_dir)
    assert ret.returncode == 0, cmd

    #生成火焰图，目的是方便用户观察perf采样是否有问题
    cmd = f"~/FlameGraph/flamegraph.pl out.folded > kernel.svg"
    subprocess.run(cmd, shell=True, cwd = run_dir)

    return os.path.join(run_dir, 'out.folded')





def perf_record_ssh(ssh_connection, binary, run_dir, run_cmd):
    '''
    Need sudo privileges to collect perf data.
    '''
    local_dir, binary_name = os.path.split(binary)
    try:
        ret = ssh_connection.put(local=binary, remote=run_dir)
    except Exception as e:
        try:
            time.sleep(3)
            ret = ssh_connection.put(local=binary, remote=run_dir)
        except Exception as e:
            assert 1==0, f'remote copy failed: from {binary} to {run_dir}'
    
    try:
        cmd = f"bash -c 'cd {run_dir} && perf record -F 999 -g -- {run_cmd}'"
        ssh_connection.sudo(cmd, timeout=2000, pty=True)
        cmd = f"bash -c 'cd {run_dir} && perf script > out.perf'"
        ssh_connection.sudo(cmd, timeout=2000, pty=True)
        # with ssh_connection.cd(run_dir):
        #     # cmd = f"sudo perf script > out.perf"
        #     # ssh_connection.run(cmd, timeout=100)
        #     cmd = f"~/FlameGraph/stackcollapse-perf.pl out.perf > out.folded"
        #     ssh_connection.run(cmd, timeout=200)
        # with ssh_connection.cd(run_dir):
        #     # cmd = f"sudo perf script > out.perf"
        #     # ssh_connection.run(cmd, timeout=100)
        #     cmd = f"~/FlameGraph/flamegraph.pl out.folded > kernel.svg"
        #     ssh_connection.run(cmd, timeout=200)
    except Exception as e:
        assert 1==0

    try:
        # ret = ssh_connection.get(os.path.join(run_dir,'out.perf'), os.path.join(local_dir,'out.perf'))
        ret = ssh_connection.get(os.path.join(run_dir,'out.perf'), local=local_dir+'/')
    except Exception as e:
        assert 1==0, f'remote get failed: from {run_dir} to {local_dir}'

    cmd = f"~/FlameGraph/stackcollapse-perf.pl out.perf > out.folded"
    ret = subprocess.run(cmd, shell=True, cwd = local_dir)
    assert ret.returncode == 0, cmd

    #生成火焰图，目的是方便用户观察perf采样是否有问题
    cmd = f"~/FlameGraph/flamegraph.pl out.folded > kernel.svg"
    subprocess.run(cmd, shell=True, cwd = local_dir)
    
    return os.path.join(local_dir, 'out.folded')

def find_elements_for_percent(data, threshold=0.95):
    # 计算总和
    total = sum(data.values())

    # 计算每个元素的百分比，并按照百分比由大到小排序
    sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
    percentages = []
    for item in sorted_data:
        percentages.append(list([item[0], item[1] / total]))

    # 计算累积百分比，找出累积达到95%的元素
    cumulative_percentage = 0
    elements_filtered = []
    x_filtered = []

    for item in percentages:
        if cumulative_percentage >= threshold or item[1] < 0.03:
            break
        cumulative_percentage += item[1]
        item.append(cumulative_percentage)
        elements_filtered.append(item)#
        x_filtered.append(item[0])
    return x_filtered,elements_filtered

def perfdata2hotfiles(module2funcnames, binary_name, folded_perf_result):
    module2cost = {}
    with open(folded_perf_result, 'r') as file:
        for line in file:
            words = line.strip().split(' ')
            names = words[0].split(';')
            for module in module2funcnames:
                if names[-1] in module2funcnames[module] and names[0] in binary_name:
                    if module not in module2cost:
                        module2cost[module] = int(words[1])
                    else:
                        module2cost[module] += int(words[1])
    
    hotfiles,elements_filtered = find_elements_for_percent(module2cost, threshold=0.95)
    for item in elements_filtered:
        print(f"{item[0]}: {item[1]*100:.2f}%, {item[2]*100:.2f}%")
    return hotfiles,elements_filtered

def gen_hotfiles(build_cmd, build_dir, tmp_dir, run_cmd, run_dir, binary, ssh_connection = None):
    fun_O3 = Function_wrap(
                    build_cmd=build_cmd, #编译命令，用户提供
                    build_dir=build_dir, #编译路径，用户提供
                    tmp_dir=tmp_dir, #数据存放目录，用户定义
                    run_cmd=run_cmd, #运行命令，用户提供
                    run_dir=run_dir, #运行路径，用户提供
                    binary=binary, #编译后的二进制文件路径，用户提供
                    ssh_connection=ssh_connection, #ssh连接
                    )
    binary_name = os.path.basename(binary)
    module2funcnames = fun_O3._get_func_names()
    fun_O3.build('default<O3>')
    try:
        shutil.rmtree(tmp_dir)
    except FileNotFoundError:
        print(f"文件夹 {tmp_dir} 不存在")
    if ssh_connection == None:
        folded_perf_result = perf_record(binary, run_dir, run_cmd)
    else:
        folded_perf_result = perf_record_ssh(ssh_connection, binary, run_dir, run_cmd)
    hotfiles,hotfiles_details = perfdata2hotfiles(module2funcnames, binary_name, folded_perf_result)
    return hotfiles, hotfiles_details
            


if __name__ == "__main__":
    pass
    # func_names = get_func_names('/home/jiayu/cBench_V1.1/security_sha/src_work/sha.bc')
    # print(func_names)


# def find_hot_files(pgo_dir, profdata):
#     # 遍历目录
#     IRs=[]
#     for entry in os.listdir(pgo_dir):
#         # 构建完整的文件路径
#         full_path = os.path.join(pgo_dir, entry)
#         # 检查这个路径是否是目录
#         assert os.path.isdir(full_path)
#         for ttt in os.listdir(full_path):
#             IRs.append(os.path.join(full_path,ttt,entry+'.bc'))

#     counts = []
#     files =[]
#     for IR in IRs:
#         IR_path, IR_name = os.path.split(IR)
#         fileroot, fileext= os.path.splitext(IR_name)
#         files.append(fileroot)
#         IR_pgouse=os.path.join(IR_path, fileroot +'.pgouse.bc')
#         cmd = f'opt -pgo-instr-use --pgo-test-profile-file={profdata} {IR} -o {IR_pgouse}'
#         ret = subprocess.run(cmd, shell=True, capture_output=True)
#         assert ret.returncode == 0, cmd

#         current_path = os.getcwd()
#         ir2dictpass = os.path.join(current_path, '../ir2count/build/lib/libir2count.so')
#         # ir2dictpass='/home/jiayu/LLVMTuner_v3/ir2count/build/lib/libir2count.so'
#         cmd=f'opt -load-pass-plugin {ir2dictpass} -passes=ir2dict -disable-output {IR_pgouse}'
#         ret = subprocess.run(cmd, shell=True, capture_output=True)
#         assert ret.returncode == 0, cmd
#         count = int(ret.stdout.decode('utf-8').strip())
#         print(IR_name, count)
#         counts.append(count)

    
#     ratios = np.array(counts)/np.sum(counts)
#     b=np.sort(ratios)[::-1]
#     ind = np.argsort(ratios)[::-1]
#     files=np.array(files)[ind]
    
#     cumratios=np.cumsum(b)
#     a = files[cumratios<0.99]
#     hot_files = files[:len(a)+1]
#     print(b[:len(a)+1])
#     print(cumratios[:len(a)+1])
#     print(hot_files)
#     return [list(hot_files),list(cumratios[:len(a)+1])]



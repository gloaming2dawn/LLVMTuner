import numpy as np
import time
import subprocess
import os
import shutil
import hashlib
import json
import re
import invoke
from math import inf
from multiprocessing import Pool

def get_directory_contents(directory):
    """
    获取指定目录的内容列表（文件和子目录）。
    """
    return set(os.listdir(directory))

def reset_directory(directory, original_contents):
    """
    将目录恢复到原始状态。
    """
    current_contents = set(os.listdir(directory))
    extra_files = current_contents - original_contents
    for extra_file in extra_files:
        file_or_dir = os.path.join(directory, extra_file)
        if os.path.isfile(file_or_dir):
            os.remove(file_or_dir)
        elif os.path.isdir(file_or_dir):
            shutil.rmtree(file_or_dir)
    missing_files = original_contents - current_contents
    for missing_file in missing_files:
        source_file_or_dir = os.path.join(original_directory, missing_file)
        if os.path.isfile(source_file_or_dir):
            shutil.copy(source_file_or_dir, directory)
        elif os.path.isdir(source_file_or_dir):
            shutil.copytree(source_file_or_dir, os.path.join(directory, missing_file))

def get_directory_contents_ssh(connection, directory):
    """
    获取指定目录的内容列表（文件和子目录）。
    """
    with connection.cd(directory):
        result = connection.run('ls -a', hide=True)
        return set(result.stdout.strip().split('\n'))

def reset_directory_ssh(connection, directory, original_contents):
    """
    将目录恢复到原始状态。
    """
    with connection.cd(directory):
        current_contents = get_directory_contents_ssh(connection, directory)
        extra_files = current_contents - original_contents
        for extra_file in extra_files:
            connection.run(f'rm -rf {extra_file}')  # 删除多余的文件或目录
        # missing_files = original_contents - current_contents
        # for missing_file in missing_files:
        #     connection.put(missing_file, directory)  # 上传缺失的文件或目录

class run_and_eval:
    def __init__(self, run_cmd, run_dir, binary, timeout=1000):
        self.run_cmd = f'time timeout {timeout} ' + run_cmd
        self.run_dir = run_dir
        self.binary = binary

    def __call__(self):
        #如果编译后的binary不在运行目录，复制文件到运行目录
        binary_dir = os.path.dirname(self.binary)
        if not os.path.samefile(binary_dir, self.run_dir):
            shutil.copy(self.binary, self.run_dir)

        original_contents = get_directory_contents(self.run_dir)

        ret = subprocess.run(self.run_cmd, shell=True, cwd=self.run_dir, capture_output=True, executable="/bin/bash")
        if ret.returncode != 0:
            runtime = inf
        else:
            temp=ret.stderr.decode('utf-8').strip()
            real=temp.split('\n')[-3]
            searchObj = re.search( r'real\s*(.*)m(.*)s.*', real)
            runtime = int(searchObj[1])*60+float(searchObj[2])

        # 重置运行目录，保证每次运行时不受到生成文件的影响
        current_contents = get_directory_contents(self.run_dir)
        if current_contents != original_contents:
            reset_directory(current_directory, original_contents)
        return runtime

class run_and_eval_ssh:
    def __init__(self, run_cmd, run_dir, binary, ssh_connection, timeout=1000):
        self.run_cmd = f'time timeout {timeout} ' + run_cmd
        self.run_dir = run_dir
        self.binary = binary
        self.ssh_connection = ssh_connection

    def __call__(self):
        try:
            ret = self.ssh_connection.put(local=self.binary, remote=self.run_dir)
        except Exception as e:
            try:
                time.sleep(3)
                ret = self.ssh_connection.put(local=self.binary, remote=self.run_dir)
            except Exception as e:
                try:
                    time.sleep(3)
                    ret = self.ssh_connection.put(local=self.binary, remote=self.run_dir)
                except Exception as e:
                    assert 1==0, f'remote copy failed: from {self.binary} to {self.run_dir}'


        original_contents = get_directory_contents_ssh(self.ssh_connection, self.run_dir)

        try:
            with self.ssh_connection.cd(self.run_dir):
                ret=self.ssh_connection.run(self.run_cmd, hide=True)
            temp=ret.stderr.strip()
            real=temp.split('\n')[-3]
            searchObj = re.search( r'real\s*(.*)m(.*)s.*', real)
            runtime = int(searchObj[1])*60+float(searchObj[2])
        except invoke.exceptions.UnexpectedExit:
            runtime = inf
        except invoke.exceptions.CommandTimedOut:
            runtime = inf
        except Exception as e:
            # 捕获其他可能的异常并进行处理
            # print("An error occurred:", e)
            runtime = inf

        # 重置运行目录，保证每次运行时不受到生成文件的影响
        current_contents = get_directory_contents_ssh(self.ssh_connection, self.run_dir)
        if current_contents != original_contents:
            reset_directory_ssh(self.ssh_connection, self.run_dir, original_contents)
        return runtime

def cxxfilt(name):
    cmd = f'c++filt -p {name}'
    ret = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert ret.returncode == 0, cmd
    return ret.stdout.strip()

def get_func_names(IR_path):
    file_b_path = os.path.abspath(__file__)
    dir_b_path = os.path.dirname(file_b_path)
    lib_path = os.path.join(dir_b_path, '../FuncNames/build/libFuncNames.so')
    cmd = f'opt -load-pass-plugin {lib_path} -passes=func-names -disable-output {IR_path}'
    ret = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
    assert ret.returncode == 0, cmd
    func_names = ret.stderr.strip().split('\n')
    func_names = [cxxfilt(x) for x in func_names if x !=''] #过滤掉空字符串
    return func_names




if __name__ == "__main__":
    # func_names = get_func_names('/home/jiayu/cBench_V1.1/security_sha/src_work/sha.bc')
    func_names = get_func_names('/home/jiayu/result_llvmtuner_17/SPEC/541.leela_r/perf/FastState/IR-21e35be40cf52e85e56de4dfc5680c6a/FastState.opt.bc')
    print(func_names)


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



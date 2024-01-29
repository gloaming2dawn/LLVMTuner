import numpy as np
import time
import subprocess
import os
import hashlib
import json
from multiprocessing import Pool



def find_hot_files(pgo_dir, profdata):
    # 遍历目录
    IRs=[]
    for entry in os.listdir(pgo_dir):
        # 构建完整的文件路径
        full_path = os.path.join(pgo_dir, entry)
        # 检查这个路径是否是目录
        assert os.path.isdir(full_path)
        for ttt in os.listdir(full_path):
            IRs.append(os.path.join(full_path,ttt,entry+'.bc'))

    counts = []
    files =[]
    for IR in IRs:
        IR_path, IR_name = os.path.split(IR)
        fileroot, fileext= os.path.splitext(IR_name)
        files.append(fileroot)
        IR_pgouse=os.path.join(IR_path, fileroot +'.pgouse.bc')
        cmd = f'opt -pgo-instr-use --pgo-test-profile-file={profdata} {IR} -o {IR_pgouse}'
        ret = subprocess.run(cmd, shell=True, capture_output=True)
        assert ret.returncode == 0, cmd

        current_path = os.getcwd()
        ir2dictpass = os.path.join(current_path, '../ir2count/build/lib/libir2count.so')
        # ir2dictpass='/home/jiayu/LLVMTuner_v3/ir2count/build/lib/libir2count.so'
        cmd=f'opt -load-pass-plugin {ir2dictpass} -passes=ir2dict -disable-output {IR_pgouse}'
        ret = subprocess.run(cmd, shell=True, capture_output=True)
        assert ret.returncode == 0, cmd
        count = int(ret.stdout.decode('utf-8').strip())
        print(IR_name, count)
        counts.append(count)

    
    ratios = np.array(counts)/np.sum(counts)
    b=np.sort(ratios)[::-1]
    ind = np.argsort(ratios)[::-1]
    files=np.array(files)[ind]
    
    cumratios=np.cumsum(b)
    a = files[cumratios<0.99]
    hot_files = files[:len(a)+1]
    print(b[:len(a)+1])
    print(cumratios[:len(a)+1])
    print(hot_files)
    return [list(hot_files),list(cumratios[:len(a)+1])]



# -*- coding: utf-8 -*-
"""
Created on Mon Dec 12 17:27:53 2022

@author: jiayu
"""
from fabric import Connection
import os 
import subprocess
import random as random
import llvmtuner
from llvmtuner import searchspace
passes = llvmtuner.searchspace.default_space()

ben2num={'automotive_bitcount':5, 'automotive_qsort1': 10,'automotive_susan_c':50, 'automotive_susan_e':20, 'automotive_susan_s':5,'bzip2d':3,'bzip2e':2,'consumer_jpeg_c':100,'consumer_lame':10, 'consumer_tiffmedian':200,'network_dijkstra':100000,'network_patricia':5000,'office_rsynth':50,'security_blowfish_d':5000, 'security_blowfish_e':5000, 'security_sha':8000, 'telecom_adpcm_c':500,'telecom_adpcm_d':1000, 'telecom_CRC32':50, 'telecom_gsm':20}

cflags='-I. -DLAMESNDFILE -DHAVEMPGLIB -DLAMEPARSE -DSASR -DSTUPID_COMPILER -DNeedFunctionPrototypes=1'

cross_flags='--target=aarch64-linux-gnu --sysroot=/home/jiayu/gcc-4.8.5-aarch64/install/aarch64-unknown-linux-gnu/sysroot/ --gcc-toolchain=/home/jiayu/gcc-4.8.5-aarch64/install'


host="nvidia@TX2-{}.local".format(1)
sshC=Connection(host=host)
 

for benchmark in ben2num:
    print(benchmark)
    ben_dir = os.path.expanduser('~/cBench_V1.1/{}/src_work/'.format(benchmark))
    run_dir = '/home/nvidia/cBench_V1.1/{}/src_work/'.format(benchmark)
    
    
    directory=os.path.expanduser('~/cBench_V1.1/{}/src_work/'.format(benchmark))
    f_list = os.listdir(directory)
    sources=[]
    objs=[]
    for f in f_list:
        fileroot,fileext = os.path.splitext(f)
        if fileext == '.c':
            source = os.path.join(directory, f)
            IR = os.path.join(directory, fileroot+'.bc')
            IRpgogen = os.path.join(directory, fileroot+'.pgogen.bc')
            obj = os.path.join(directory, fileroot+'.o')
            objs.append(obj)
            
            cmd = f'clang -emit-llvm -c -O3 -Xclang -disable-llvm-optzns {cflags} {cross_flags} {source} -o {IR}'
            ret=subprocess.run(cmd, shell=True, cwd=directory, capture_output=True)
            assert ret.returncode==0
            
            # cmd=f'clang -emit-llvm -c -O3 -Xclang -disable-llvm-optzns {cflags} {source} -o {IR}'
            # ret=subprocess.run(cmd, shell=True, cwd=directory, capture_output=True)
            # assert ret.returncode==0
            
            # cmd=f'clang -emit-llvm -c -O1 -Xclang -disable-llvm-optzns {source} -o {IR1}'
            # cmd=f'diff {IR} {IR1}'
            
            cmd=f'opt -pgo-instr-gen -instrprof {IR} -o {IRpgogen}'#
            ret=subprocess.run(cmd, shell=True, cwd=directory, capture_output=True)
            assert ret.returncode==0
            cmd=f'clang -O3 -xir -c {IRpgogen} {cflags} {cross_flags} -o {obj}'# -flto -fuse-ld=lld
            ret=subprocess.run(cmd, shell=True, cwd=directory, capture_output=True)
            assert ret.returncode==0
    
    
    
    objs_str = ' '.join(objs)
    output = os.path.join(directory, 'a.out')
    cmd = f'clang -O3 -fprofile-generate {objs_str} {cflags} {cross_flags} -o {output} -lm' # -fprofile-instr-generate  -flto -fuse-ld=lld 
    subprocess.run(cmd, shell=True, cwd=directory)
    ret=subprocess.run(cmd, shell=True, cwd=directory, capture_output=True)
    assert ret.returncode==0, cmd
    
    # output = os.path.join(directory, 'a.out')
    # cmd = f'clang -O0 -fprofile-generate *.c {cflags} {cross_flags} -o {output} -flto -fuse-ld=lld -lm' # -fprofile-instr-generate 
    # subprocess.run(cmd, shell=True, cwd=directory)
    # ret=subprocess.run(cmd, shell=True, cwd=directory, capture_output=True)
    # assert ret.returncode==0
    
    
    sshC.put(local=os.path.join(ben_dir,'a.out'), remote=run_dir)
    run_cmd = f'LLVM_PROFILE_FILE="default.profraw" ./__run 1 {ben2num[benchmark]}'
    # run_cmd = 'LLVM_PROFILE_FILE="default.profraw" ./__run 1 {}'.format(ben2num[benchmark])
    with sshC.cd(run_dir):
        ret=sshC.run(run_cmd, hide=True)
    assert ret.return_code == 0
    
    # cmd = f'LLVM_PROFILE_FILE="default.profraw" ./__run 1 1'
    # ret=subprocess.run(cmd, shell=True, cwd=directory, capture_output=True)
    # assert ret.returncode==0
    
    sshC.get(remote=os.path.join(run_dir, 'default.profraw'), local=ben_dir)
    
    cmd = 'llvm-profdata merge default.profraw -o default.profdata'
    ret=subprocess.run(cmd, shell=True, cwd=directory, capture_output=True)
    assert ret.returncode==0
    
    
    for f in f_list:
        fileroot,fileext = os.path.splitext(f)
        if fileext == '.c':
            source = os.path.join(directory, f)
            IR = os.path.join(directory, fileroot+'.bc')
            IRpgouse = os.path.join(directory, fileroot+'.pgouse.bc')
            # cmd = f'clang -emit-llvm -c -O3 -Xclang -disable-llvm-optzns --target=aarch64-linux-gnu --sysroot=/home/jiayu/gcc-4.8.5-aarch64/install/aarch64-unknown-linux-gnu/sysroot/ --gcc-toolchain=/home/jiayu/gcc-4.8.5-aarch64/install {cflags} {source} -o {IR}'
            # ret=subprocess.run(cmd, shell=True, cwd=directory, capture_output=True)
            # assert ret.returncode==0
            #-strip-named-metadata
            cmd = f'opt -pgo-instr-use --pgo-test-profile-file=default.profdata {IR} -o {IRpgouse}'
            subprocess.run(cmd, shell=True, cwd=directory)
            
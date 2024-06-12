# -*- coding: utf-8 -*-
import time
from copy import deepcopy
# import numpy as np
import json
import os
import subprocess
import sys
import hashlib
from pathlib import Path
# from multiprocessing import Pool
import fcntl
# import time
# import invoke
# import re
# from sklearn import preprocessing
# from utils import Tracker
# import shutil
# from asm2vec import get_BBinfo
# from sklearn.preprocessing import OneHotEncoder
# import numpy as np
# enc = OneHotEncoder(handle_unknown='error')
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--opt-cfg-json', help='')
parser.add_argument('--gen-ir', default=False, action='store_true', 
                    help='whether to only generate IR or to finish the whole compilation command')
parser.add_argument('--instrument-ir', default=False, action='store_true', 
                    help='whether to instrument in IR level for generating profdata')
parser.add_argument('--profdata', help='')
parser.add_argument('--optlevel', default='-O3', help='')
parser.add_argument('--llvm-dir', default='', help='')
# parser.add_argument('--hotfiles', help='')
args, unknown = parser.parse_known_args()


def create_file(output):
    # 获取文件锁
    with open(output, "w") as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        # 检查文件是否已经存在
        script_content = '#!/bin/bash\necho "fake build!"\n'
        file.write(script_content)
        os.chmod(output, 0o755)
        # if not os.path.exists(output):
        #     file.write(script_content)
        # 释放文件锁
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)

class Clangopt:
    def __init__(self):
        '''
        初始化功能：（1）使用clang的-MJ命令生成compilation database；（2）从compilation database中获取编译信息
        '''
        if not args.opt_cfg_json:
            self.params='default<O3>'
            self.tmp_dir=os.path.join(os.path.expanduser('~/'), './tmp/')
            self.hotfiles=None
        else:
            # 判断配置文件是否存在
            assert os.path.isfile(args.opt_cfg_json)
            # 读取配置文件中的优化参数
            with open(args.opt_cfg_json, "r") as f:
                cfg=json.load(f)
            self.params=cfg['params']
            self.tmp_dir=cfg['tmp_dir']
            self.hotfiles=cfg['hotfiles'] if 'hotfiles' in cfg else None
        os.makedirs(self.tmp_dir,exist_ok=True) 
        
        # 使用clang的-MJ命令生成compilation database
        # maybe we could also use clang -###
        clang_cmd=['clang']+unknown
        self.clang_cmd = clang_cmd
        print(' '.join(self.clang_cmd))
        
        optlevels=['-O3','-O2','-O1','-O0','-Oz','-O4','-Ofast','-Og','-Os']
        cmd=[x for x in clang_cmd if x not in optlevels ]
        cmd=' '.join(cmd)
        hash_str=hashlib.md5((cmd+str(self.params)).encode('utf-8')).hexdigest() 
        MJfile=os.path.join(self.tmp_dir, f'MJ-{hash_str}.json')
        cmd = cmd + ' -MJ {} ---xxx'.format(MJfile)
        ret = subprocess.run(cmd, shell=True, capture_output=True)
        
        self.objs=[]
        if '-c' in clang_cmd or '-S' in clang_cmd:
            self.link=False
        else:
            #意味着该命令形式为 clang *.c 或者 clang *.o
            self.link=True
        
        # 从compilation database中获取编译信息
        if os.path.isfile(MJfile):
            with open(MJfile,"r") as f:
                cdb = [json.loads(line[:-2]) for line in f]
            os.remove(MJfile)
            # assert 1==0, MJfile
            self.cdb=cdb
        # 如果该命令为链接obj文件生成二进制
        else:
            self.cdb = None
        
            
        
        
    
    def _single_compile(self, x):
        source=x['file']
        reldir,filename=os.path.split(source)
        fileroot,fileext=os.path.splitext(filename)
        
        if self.hotfiles and fileroot not in self.hotfiles: 
            opt_str = args.optlevel
        else:
            if isinstance(self.params, (str)):
                opt_str=self.params
            else:
                opt_str=self.params[fileroot]
        
        
        
        
        IR_dir=os.path.join(self.tmp_dir, fileroot, 'IR-{}/'.format( hashlib.md5(opt_str.encode('utf-8')).hexdigest()))
        os.makedirs(IR_dir, exist_ok=True)
        
        
        with open(os.path.join(IR_dir, 'seq.json'),'w') as ff:
            json.dump(opt_str, ff, indent=4)
        
        
        
        directory=x['directory']
        obj=x['output']
        
        self.objs.append(obj)
        
        IR=os.path.join(IR_dir, fileroot +'.bc')
        IR_pgouse=os.path.join(IR_dir, fileroot +'.pgouse.bc')
        IR_opt=os.path.join(IR_dir,fileroot+'.opt.bc')
        obj_cp = os.path.join(IR_dir,fileroot+'.o')
        
        asm=os.path.join(IR_dir, fileroot+'.s')
        opt_stats=os.path.join(IR_dir, fileroot+'.opt_stats')
        bfi=os.path.join(IR_dir, fileroot +'.bfi')
        cmd = deepcopy(self.clang_cmd)
        # cmd=x['arguments']
        if '-o' in cmd:
            j=cmd.index('-o')
            del cmd[j:j+2]
        cmd=[x for x in cmd if x!='---xxx' and x!='-c' and x!='-S' and not x.endswith('.c') and not x.endswith('.cpp') and not x.endswith('.cc') and not x.endswith('.cxx') and not x.endswith('.C')]
        cflags = ' '.join(cmd[1:])
        
        if args.instrument_ir or not os.path.isfile(IR_opt):#
            self.source2IR(args.llvm_dir, source, cflags, args.optlevel, IR, cwd=directory)
            flag = self.opt(args.llvm_dir, opt_str, IR, IR_pgouse, IR_opt, opt_stats, bfi)
            assert flag
            # if not flag:
            #     IR_dir=os.path.join(self.tmp_dir, fileroot, 'IR-{}/'.format( hashlib.md5('default<O3>'.encode('utf-8')).hexdigest()))
            #     IR_opt = os.path.join(IR_dir,fileroot+'.opt.bc')
            # return flag
        
            # if not flag:
            #     flag = self.opt(args.llvm_dir, '-O3', IR, IR_pgouse, IR_opt, opt_stats, bfi)
            #     assert flag
        
        if not args.gen_ir: #
            if not os.path.isfile(obj_cp):
                flag = self.IR2obj(args.llvm_dir, IR_opt, obj, obj_cp, cflags, cwd=directory)
                assert flag
            else:
                cp_cmd = f'cp {obj_cp} {obj}'
                ret = subprocess.run(cp_cmd, cwd=directory, shell=True, capture_output=True)
                assert ret.returncode == 0
        else:
            if not os.path.isfile(obj_cp):
                flag = self.IR2obj(args.llvm_dir, IR_opt, obj_cp, None, cflags, cwd=directory)
                assert flag

        return True
            # if not flag:
            #     flag = self.opt(args.llvm_dir, '-O3', IR, IR_pgouse, IR_opt, opt_stats, bfi)
            #     assert flag
            #     flag = self.IR2obj(args.llvm_dir, IR_opt, obj, obj_cp, cwd=directory)
            #     assert flag
    
    def _compile(self):
        final_flag=True
        # 如果该命令为链接obj文件生成二进制
        if self.cdb == None:
            if args.instrument_ir:
                link_cmd = ' '.join(self.clang_cmd) + ' -fprofile-generate'
            else:
                link_cmd = ' '.join(self.clang_cmd)
            print(link_cmd)

            if not args.gen_ir:#如果是正常build
                ret = subprocess.run(link_cmd, cwd =os.getcwd(), shell=True, capture_output=True)
                assert ret.returncode == 0, [os.getcwd(), link_cmd]
                # if '-o' in self.clang_cmd:
                #     j = self.clang_cmd.index('-o')
                #     output = self.clang_cmd[j+1]
                # else:
                #     output = 'a.out'
                # cp_cmd = f'cp {output} {tmp_dir}'
                # ret = subprocess.run(cp_cmd, shell=True, capture_output=True)
                # assert ret.returncode == 0
            else:#如果只是生成IR，而不是生成最终二进制
                if '-o' in self.clang_cmd:
                    j = self.clang_cmd.index('-o')
                    outputname = self.clang_cmd[j+1]
                else:
                    outputname = 'a.out'
                output = os.path.join(os.getcwd(), outputname)
                if not os.path.exists(output): #编译脚本中可能会对生成的binary做copy之类的操作，为避免报错，创建一个假文件
                    # ret = subprocess.run(link_cmd, cwd =os.getcwd(), shell=True, capture_output=True)
                    # assert ret.returncode == 0, [os.getcwd(), link_cmd]
                    create_file(output)
                return

        
        else:
            if self.hotfiles: 
                for x in self.cdb:
                    reldir,filename = os.path.split(x['file'])
                    fileroot,fileext=os.path.splitext(filename)
                    if fileroot in self.hotfiles:
                        flag = self._single_compile(x)
                        if not flag:
                            final_flag=False
                        # 改变源文件时间戳保证下次仍然会重新编译
                        Path(x['file']).touch()
            else:
                for x in self.cdb:
                    flag = self._single_compile(x)
                    if not flag:
                        final_flag=False
                    # 改变源文件时间戳保证下次仍然会重新编译
                    Path(x['file']).touch()
            
            
            if self.link:#如果命令为clang *.c -o a.out形式，既有编译为.o也有链接.o为目标文件的操作
                
                link_cmd_wo_objs = [aa for aa in self.clang_cmd if not aa.endswith('.c') and not aa.endswith('.cpp') and not aa.endswith('.cc') and not aa.endswith('.cxx')]
                link_cmd_wo_objs = ' '.join(link_cmd_wo_objs)
                
                
                if '-o' in self.clang_cmd:
                    j = self.clang_cmd.index('-o')
                    output = self.clang_cmd[j+1]
                else:
                    output = 'a.out'
                objs_str = ' '.join(self.objs)
                
                if args.instrument_ir:
                    link_cmd = f'{link_cmd_wo_objs} {objs_str} -fprofile-generate'
                else:
                    link_cmd = f'{link_cmd_wo_objs} {objs_str}'
                ret = subprocess.run(link_cmd, shell=True, capture_output=True)
                assert ret.returncode == 0, link_cmd
                
    

    @staticmethod
    def runcmd(cmd, cwd=None, timeout=None):
        '''
        用于执行命令行cmd命令，如果命令执行出错或者超时则输出相应信息，
        这里接受的cmd是一个string, cwd是当前工作路径
        '''
        try:
            ret=subprocess.run(cmd, cwd=cwd, capture_output=True,shell=True,timeout=timeout)
            assert ret.returncode == 0, [cmd,cwd]
            if ret.returncode == 0:
                flag=True
            else:
                flag=False
        except subprocess.TimeoutExpired:
            flag=False
            ret=None
        return flag, ret
    
    
    @classmethod
    def source2IR(cls, llvm_dir, source, cflags, optlevel, output, cwd=None):
        if args.instrument_ir:
            cmd = f'{os.path.join(llvm_dir,"clang")} {cflags} -emit-llvm -c {optlevel} {source} -o {output}'
            flag, ret = cls.runcmd(cmd, cwd)
            assert flag == True, 'Check command in {}: {}'.format(cwd, cmd)
        else:
            cmd = f'{os.path.join(llvm_dir,"clang")} {cflags} -emit-llvm -c {optlevel} -Xclang -disable-llvm-optzns {source} -o {output}'
            flag, ret = cls.runcmd(cmd, cwd)
            assert flag == True, 'Check command in {}: {}'.format(cwd, cmd)

        
    
    
    @classmethod
    def opt(cls, llvm_dir, opt_params,  IR, IR_pgouse, IR_opt, opt_stats, bfi, cwd=None):            
        if args.instrument_ir:
            cmd=f'opt -pgo-instr-gen -instrprof {IR} -o {IR_opt}'
            flag, ret = cls.runcmd(cmd, cwd)
            assert flag == True, cmd
            return flag


        if args.profdata and args.profdata != 'None':
            cmd = f'{os.path.join(llvm_dir,"opt")} -pgo-instr-use --pgo-test-profile-file={args.profdata} {IR} -o {IR_pgouse}'
            flag, ret = cls.runcmd(cmd, cwd)
            assert flag == True, cmd
            
        else:
            IR_pgouse = IR
        
        # cmd = os.path.join(llvm_dir,'opt')+' -enable-new-pm=0 {} {} -o {} -stats -stats-json 2> {}'.format(opt_params, opt_input, opt_output, opt_stats)
        cmd = f'{os.path.join(llvm_dir,"opt")} -passes="{opt_params}" {IR_pgouse} -o {IR_opt} -stats -stats-json 2> {opt_stats}'
        flag, ret = cls.runcmd(cmd, cwd)
        if not flag:
            os.remove(opt_stats)
        # os.remove(IR_pgouse)
        os.remove(IR)
        assert flag == True, cmd
        return flag
    
    
    @classmethod
    def IR2obj(cls, llvm_dir, IR_opt, obj, obj_cp, cflags, cwd=None):
        # if args.instrument_ir:
        #     cmd=f'clang {args.optlevel} -xir -c {IR_opt} {cflags} -o {obj}'
        #     flag, ret = cls.runcmd(cmd, cwd)
        #     assert flag == True, cmd
        #     return flag
        
        # cmd = os.path.join(llvm_dir,'llc')+'  -O3 {} -o {} --print-machine-bfi 2> {}'.format(IR_opt, asm, machinebfi)
        cmd = os.path.join(llvm_dir,'llc')+' -O3 -filetype=obj -relocation-model=pic {} -o {}'.format(IR_opt, obj)
        # cmd = os.path.join(llvm_dir,'llc')+' -O3 -filetype=obj {} -o {}'.format(IR_opt, obj)
        # cmd = os.path.join(llvm_dir,'clang')+' -c {} -o {}'.format(IR_opt, obj)
        flag, ret = cls.runcmd(cmd, cwd)
        print(cmd,cwd)
        assert flag == True, cmd
        
        if obj_cp != None:
            cp_cmd = f'cp {obj} {obj_cp}'
            ret = subprocess.run(cp_cmd, cwd=cwd, shell=True, capture_output=True)
            assert ret.returncode == 0
        
        return flag
    
    
    
def main():
    # with open(args.opt_cfg_json, "w") as f:
    #     json.dump('-O3', f)
    # clangopt_cmd=sys.argv
    # print('command options:', clangopt_cmd)
    
    clangopt=Clangopt()
    clangopt._compile()

    
if __name__ == "__main__":   
    
    print('command options:', unknown)
    clangopt=Clangopt()
    clangopt._compile()
    # clangopt=Clangopt(clangopt_cmd)
    # clangopt._compile()

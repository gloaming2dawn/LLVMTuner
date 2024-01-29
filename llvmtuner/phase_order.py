# -*- coding: utf-8 -*-
"""
Created on Tue Mar  1 12:48:39 2022

@author: scjzhadmin
"""
from copy import deepcopy
import numpy as np
import json
import os
import subprocess
from multiprocessing import Pool
import time
import invoke
import re
from sklearn import preprocessing
from utils import Tracker
import shutil
from asm2vec import get_BBinfo
from sklearn.preprocessing import OneHotEncoder
import numpy as np
enc = OneHotEncoder(handle_unknown='error')

class Phaseorder:
    def __init__(self, sources, cflags, lflags, build_dir, exename, runcmds, run_dir, diffcmds=None, diff_true_result=None, copy_O3_cmds=None, connection=None, host=None, cross_linker=None, march='', mcpu='native'):
        self.sources=sources
        self.cflags=cflags
        self.lflags=lflags
        self.build_dir=build_dir
        self.exe=exename
        
        self.runcmds=runcmds
        self.run_dir=run_dir
        self.diffcmds=diffcmds
        self.diff_true_result=diff_true_result
        self.copy_O3_cmds=copy_O3_cmds
        
        self.cross_compile=False
        if connection != None:
            self.cross_compile=True
        self.connection=connection
        self.host=host
        self.cross_linker=cross_linker
        self.march=march
        self.mcpu=mcpu
        
        self.max_opt_time, self.max_llc_time, self.max_link_time, self.max_run_time = 1e3,1e3,1e3,1e3
        
        # Initial profile to obtain profile data
        self.initial_profile()
        # At the first time, compile all sources to unoptimized IRs
        self.source2IR(' '.join(self.sources), '-fno-discard-value-names -fprofile-instr-use=foo.profdata'+' '+self.cflags, cwd=self.build_dir)
        
        self.best_y = float("inf")
        
        self.ms2y={} # md5sum is key, y (runtime) is value
        self.seqs=set()
    
    @staticmethod
    def runcmd(cmd, cwd=None, timeout=None):
        '''
        用于执行命令行cmd命令，如果命令执行出错或者超时则输出相应信息，
        这里接受的cmd是一个string,cwd是当前工作路径
        '''
        try:
            ret=subprocess.run(cmd, cwd=cwd, capture_output=True,shell=True,timeout=timeout)
            if ret.returncode == 0:
                flag=True
            else:
                flag=False
        except subprocess.TimeoutExpired:
            flag=False
            ret=None
        return flag, ret
    
    
    def runcmd_ssh(self, cmd, cwd=None, timeout=None):
        '''
        用于远程通过ssh执行命令行cmd命令，如果命令执行出错或者超时则输出相应信息，
        这里接受的cmd是一个string,cwd是当前工作路径
        '''
        
        try:
            time.sleep(0.1)
            with self.connection.cd(cwd):
                ret=self.connection.run(cmd, hide=True, timeout=timeout)
            if ret.return_code == 0:
                flag=True
            else:
                flag=False
                print('cmd failed: {}'.format(cmd))
        except invoke.exceptions.UnexpectedExit:
            flag=False
            ret=None
            print('cmd failed: {}'.format(cmd))
        except invoke.exceptions.CommandTimedOut:
            # print('timeout')
            flag=False
            ret=None
        return flag, ret
    
    def run(self, cross_compile=True, diff=True, cmd_prefix='time '):
        '''
        run exe and compare outputs with expected outputs. 
        if execution failed or outputs differ, return a large number, otherwise return runtime
        '''
        if cross_compile:
            cmd='rsync -av {} {}'.format(self.exe, self.host+':'+self.run_dir)
            flag,ret=self._runcmd(cmd, cwd=self.build_dir)
            if not flag:
                # try again if rsync failed
                flag,ret=self._runcmd(cmd, cwd=self.build_dir)
            if not flag:
                flag,ret=self._runcmd(cmd, cwd=self.build_dir)
            if not flag:
                flag,ret=self._runcmd(cmd, cwd=self.build_dir)
            if not flag:
                flag,ret=self._runcmd(cmd, cwd=self.build_dir)
            if not flag:
                flag,ret=self._runcmd(cmd, cwd=self.build_dir)
            if not flag:
                flag,ret=self._runcmd(cmd, cwd=self.build_dir)
            assert flag == True, 'Check command in {}: {}'.format(self.build_dir,cmd)
        
        runtime=0
        for cmd in self.runcmds:
            if cross_compile:
                flag,ret = self.runcmd_ssh(cmd_prefix+cmd, cwd=self.run_dir,timeout=self.max_run_time)
            else:
                flag,ret = self.runcmd(cmd_prefix+cmd, cwd=self.run_dir,timeout=self.max_run_time)
            if not flag:
                return self.max_run_time
            if cmd_prefix == 'time ':
                temp=ret.stderr.strip()
                temp=temp.split('\n')[-3]
                searchObj = re.search( r'real\s*(.*)m(.*)s.*', temp)
                runtime += int(searchObj[1])*60+float(searchObj[2])
                if runtime>self.max_run_time:
                    return self.max_run_time

        if self.diffcmds != None and diff:
            for i in range(len(self.diffcmds)):
                cmd=self.diffcmds[i]
                flag,ret = self.runcmd_ssh(cmd, cwd=self.run_dir)
                assert flag == True, 'Check command in {}: {}'.format(self.run_dir,cmd)
                if ret.stdout.strip() != self.diff_true_result:
                    print('different outputs')
                    return self.max_run_time
        return runtime
    
    @classmethod
    def source2IR(cls, sources, cflags, cwd=None):
        cmd = 'clang -emit-llvm -c -O1 -Xclang -disable-llvm-optzns {} {}'.format(cflags, sources)
        flag, ret = cls.runcmd(cmd, cwd)
        assert flag == True, 'Check command in {}: {}'.format(cwd, cmd)
    
    @classmethod
    def opt(cls, pass_seq, IR, IR_opt_name, cwd=None):
        cmd = 'opt -enable-new-pm=0 {} {} -o {}'.format(pass_seq,IR,IR_opt_name)
        flag, ret = cls.runcmd(cmd, cwd)
        assert flag == True, [cmd,cwd]
        return flag, ret
    
    @classmethod
    def IR2asm(cls, IR_opt_name, asm_name, bfi_name, cwd=None):
        cmd = 'llc -O3 {} -o {} --print-machine-bfi 2> {}'.format(IR_opt_name, asm_name, bfi_name)
        flag, ret = cls.runcmd(cmd, cwd)
        return flag, ret
    
    # @classmethod
    # def asm2exe(cls, asms, exe, lflags, cwd=None):
    #     cmd = 'clang {} -o {} {}'.format(' '.join(asms), exe, lflags)
    #     flag, ret = cls.runcmd(cmd, cwd)
    #     return flag, ret
    
    def asm2exe(self, tmp_dirname):
        assert os.path.isdir(tmp_dirname)
        asms=[]
        for source in self.sources:
            reldir,filename=os.path.split(source)
            fileroot,fileext=os.path.splitext(filename)
            asm_name = os.path.join(tmp_dirname, fileroot +'.s')
            assert os.path.isfile(asm_name)
            asms.append(asm_name)
            
        cmd = 'clang {} -o {} {}'.format(' '.join(asms), self.exe, self.lflags)
        flag, ret = self.runcmd(cmd, cwd=self.build_dir)
        if not flag:
            print(cmd, self.build_dir, ret)
        return flag, ret
    
    def initial_profile(self):
        t0=time.time()
        cmd='clang {} -O1 {} -o {} {}'.format('-fno-discard-value-names -fprofile-instr-generate -fcoverage-mapping'+' '+self.cflags, ' '.join(self.sources), self.exe, self.lflags)
        flag,ret=self.runcmd(cmd, cwd=self.build_dir)
        assert flag == True, 'Check command in {}: {}'.format(self.build_dir,cmd)
        
        runtime = self.run(diff=False, cmd_prefix='LLVM_PROFILE_FILE="foo.profraw" ')
        assert runtime == 0, 'execution at -O1 failed'
        
        if self.cross_compile:
            cmd='rsync -av {} {}'.format(self.host+':'+self.run_dir+'/foo.profraw', './foo.profraw')
            ret= subprocess.run(cmd, shell=True, capture_output=True, cwd=self.build_dir)
            assert ret.returncode == 0
        
        cmd='llvm-profdata merge foo.profraw -o foo.profdata'
        flag,ret = self.runcmd(cmd, cwd=self.build_dir)
        assert flag == True, 'Check command in {}: {}'.format(self.build_dir,cmd)
        
        print('initial profile time:',time.time()-t0)
    
    def seq2vec(self, pass_seq, tmp_dirname):
        pass_seq = ' '.join(pass_seq)
        # if os.path.isdir(tmp_dirname):
        #     shutil.rmtree(tmp_dirname)
        # os.makedirs(tmp_dirname, exist_ok=True)
        total_cycles=0
        opcodes={}
        for source in self.sources:
            reldir,filename=os.path.split(source)
            fileroot,fileext=os.path.splitext(filename)
            IR = os.path.join(reldir, fileroot +'.bc')
            IR_opt_name = os.path.join(tmp_dirname, fileroot +'.opt.bc')
            asm_name = os.path.join(tmp_dirname, fileroot +'.s')
            bfi_name = os.path.join(tmp_dirname, fileroot +'.bfi')
            flag, ret = self.opt(pass_seq, IR, IR_opt_name, cwd = self.build_dir)
            if not flag:
                return False
            flag, ret = self.IR2asm(IR_opt_name, asm_name, bfi_name)
            if not flag:
                return False
            BBinfo = get_BBinfo(asm_name, bfi_name, march=self.march, mcpu=self.mcpu, output_asm=os.path.join(tmp_dirname, fileroot +'.tmp.s'), mca_result=os.path.join(tmp_dirname, fileroot +'.mca.json'))
            for key,value in BBinfo.items():
                if value['opcodes']!= None:
                    for opcode in value['opcodes']:
                        if opcode in opcodes:
                            opcodes[opcode] += value['count']
                        else:
                            opcodes[opcode] = value['count']
                total_cycles += value['count']*value['mca_cycle']
        
        # seq2vec={pass_seq: [total_cycles, sorted(opcodes.items())]}
        seq2vec={pass_seq: [total_cycles, opcodes]}
        with open(os.path.join(tmp_dirname, 'vec.txt'), "w") as f:
            f.write(json.dumps(seq2vec) + '\n')
        
        with open(os.path.join(self.build_dir, 'vec.txt'), "a") as f:
            f.write(json.dumps(seq2vec) + '\n')
        return True
    

            


        
    
        
    def _initial_test_O3(self):
        '''
        Test at -O3 whether compilation and execution could success.
        return runtime
        '''
        t0=time.time()
        # flag,_=self._opt_compile(['-O3'])
        flag=self._opt_compile_noreduce(['-O3'], self.exe,suffix='.bc')
        O3_compile_time=time.time()-t0
        assert flag == True, 'compilation at -O3 failed'
        print('O3_compile_time',O3_compile_time)
        

        
#        t0=time.time()
#        for source in self.sources:
#            reldir,filename=os.path.split(source)
#            fileroot,fileext=os.path.splitext(filename)
#            IR=fileroot+'.bc'
#            IR_opt=fileroot+'.opt.bc'
#            cmd='opt -O3 {} -o {}'.format(IR,IR_opt)
#            flag,ret=self._runcmd(cmd, cwd=self.build_dir)
#            assert flag == True, 'Check command in {}: {}'.format(self.build_dir,cmd)
#        O3_opt_time=time.time()-t0
#        
#        t0=time.time()
#        for source in self.sources:
#            reldir,filename=os.path.split(source)
#            fileroot,fileext=os.path.splitext(filename)
#            IR_opt=fileroot+'.opt.bc'
#            obj=fileroot+'.o'
#            cmd='llc -O3 -filetype=obj {} -o {}'.format(IR_opt,obj)
#            flag,ret=self._runcmd(cmd, cwd=self.build_dir)
#            assert flag == True, 'Check command in {}: {}'.format(self.build_dir,cmd)
#        O3_llc_time=time.time()-t0
            
            
#        t0=time.time()
#        cmd='{} -O3 *.o -o {} {}'.format(self.cross_linker, exe, self.lflags)
#        flag,ret=self._runcmd(cmd, cwd=self.build_dir)
#        assert flag == True, 'Check command in {}: {}'.format(self.build_dir,cmd)
#        O3_link_time=time.time()-t0
        
#        cmd='rsync -av {} {}'.format(exe, self.host+':'+self.run_dir)
#        flag,ret=self._runcmd(cmd, cwd=self.build_dir)
#        if not flag:
#            # try again if rsync failed
#            flag,ret=self._runcmd(cmd, cwd=self.build_dir)
#        if not flag:
#            flag,ret=self._runcmd(cmd, cwd=self.build_dir)
#        assert flag == True, 'Check command in {}: {}'.format(self.build_dir,cmd)
        
        # O3_run_time=0
        # for cmd in self.runcmds:
        #     flag,ret = self.runcmd_ssh('time '+cmd, cwd=self.run_dir)
        #     assert flag == True, 'Check command in {}: {}'.format(self.run_dir,cmd)
        #     temp=ret.stderr.strip()
        #     temp=temp.split('\n')[-3]
        #     searchObj = re.search( r'real\s*(.*)m(.*)s.*', temp)
        #     O3_run_time += int(searchObj[1])*60+float(searchObj[2])

        
#        if self.diffcmds != None:
#            for i in range(len(self.diffcmds)):
#                cmd=self.diffcmds[i]
#                flag,ret=self.runcmd_ssh(cmd, cwd=self.run_dir)
#                assert flag == True, 'Check command in {}: {}'.format(self.run_dir,cmd)
#                assert ret.stdout.strip()==self.diff_true_result, 'different outputs\n'+'Check command in {}: {}'.format(self.run_dir,cmd)
        

        # O3_run_time_list=[]
        # for num in range(self.n_evals_O3):
        #     O3_run_time_list.append(self._run(diff=False))
        # if np.std(O3_run_time_list)/np.mean(O3_run_time_list) > 0.01:
        #     for num in range(self.n_evals_O3):
        #         O3_run_time_list.append(self._run(diff=False))
        # if np.std(O3_run_time_list)/np.mean(O3_run_time_list) > 0.01:
        #     for num in range(self.n_evals_O3):
        #         O3_run_time_list.append(self._run(diff=False))
        # if np.std(O3_run_time_list)/np.mean(O3_run_time_list) > 0.01:
        #     for num in range(self.n_evals_O3):
        #         O3_run_time_list.append(self._run(diff=False))
        # O3_run_time=np.mean(O3_run_time_list)
        
        O3_run_time=self._run(diff=False)
        O3_run_time_list=[O3_run_time]
        
        print('O3_run_time (should be measured multiple times)',O3_run_time,O3_run_time_list)
        self.best_y = 1.2*O3_run_time
        
        if self.copy_O3_cmds is not None:
            for i in range(len(self.copy_O3_cmds)):
                cmd=self.copy_O3_cmds[i]
                flag,ret=self.runcmd_ssh(cmd, cwd=self.run_dir)
                assert flag == True, 'Check command in {}: {}'.format(self.run_dir,cmd)
        return O3_compile_time,O3_run_time
    
    



    def _opt_compile_noreduce(self, pass_seq,exe,llc_flag='-O3',suffix='.bc'):
        '''
        apply optimization sequence to unoptimized IRs, and convert IRs to exe.
        will return false if compilation failed
        ------
        pass_seq (list): optimization sequence
        '''
#        pass_seq=list(self.le.inverse_transform(x))
        pass_seq=' '.join(pass_seq)
        
        # print(len(self.sources))
        # t0=time.time()
        # for source in self.sources:
        #     t1=time.time()
        #     reldir,filename=os.path.split(source)
        #     fileroot,fileext=os.path.splitext(filename)
        #     IR=fileroot+'.bc'
        #     IR_opt=fileroot+'.opt.bc'
        #     cmd='opt {} {} -o {}'.format(pass_seq, IR,IR_opt)
        #     flag,ret = self._runcmd(cmd, cwd=self.build_dir,timeout=self.max_opt_time)
        #     print('opt time for {}'.format(source),time.time()-t1)
        #     if not flag:
        #         return False
        #     t=time.time()-t0
        #     if t>self.max_opt_time:
        #         # print('timeout')
        #         return False
            
        # self.objs=[]
        # t0=time.time()
        # for source in self.sources:
        #     t1=time.time()
        #     reldir,filename=os.path.split(source)
        #     fileroot,fileext=os.path.splitext(filename)
        #     IR_opt=fileroot+'.opt.bc'
        #     obj=fileroot+'.o'
        #     self.objs.append(obj)
        #     cmd='llc -O3 -filetype=obj {} -o {}'.format(IR_opt,obj)
        #     flag,ret = self._runcmd(cmd, cwd=self.build_dir,timeout=self.max_llc_time)
        #     print('llc time for {}'.format(source),time.time()-t1)
        #     if not flag:
        #         return False
        #     t=time.time()-t0
        #     if t>self.max_llc_time:
        #         # print('timeout')
        #         return False
        
        cmd='rm *.o'
        flag,ret = self._runcmd(cmd, cwd=self.build_dir)

        t0=time.time()
        cmds=[]
        self.objs=[]
        for source in self.sources:
            reldir,filename=os.path.split(source)
            fileroot,fileext=os.path.splitext(filename)
            IR=fileroot+suffix
            IR_opt=fileroot+'.opt.bc'
            opt_cmd='opt {} {} -o {}'.format(pass_seq, IR, IR_opt)
            obj=fileroot+'.o'
            self.objs.append(obj)
            llc_cmd='llc {} -filetype=obj {} -o {}'.format(llc_flag, IR_opt, obj)
            cmd=opt_cmd+' && '+llc_cmd
            cmds.append(cmd)
        flag,ret = self._runcmd_parallel(cmds,cwd=self.build_dir)
        if not flag:
            print(cmds)
            return False
        
        # self.objs=[]
        # cmds=[]
        # for source in self.sources:
        #     reldir,filename=os.path.split(source)
        #     fileroot,fileext=os.path.splitext(filename)
        #     IR_opt=fileroot+'.opt.bc'
        #     obj=fileroot+'.o'
        #     self.objs.append(obj)
        #     cmd='llc {} -filetype=obj {} -o {}'.format(llc_flag, IR_opt, obj)
        #     cmds.append(cmd)
        # flag,ret = self._runcmd_parallel(cmds,cwd=self.build_dir)
        # if not flag:
        #     return False
        
        # print('compile time:',time.time()-t0)
        
        t0=time.time()
        cmd='{} -O3 {} -o {} {}'.format(self.cross_linker,' '.join(self.objs),exe, self.lflags)
        flag,ret = self._runcmd(cmd, cwd=self.build_dir)
        if not flag:
            return False
        
        # print('link time:',time.time()-t0)
        
        return True
    
    def _opt_compile(self, pass_seq):
        '''
        apply optimization sequence to unoptimized IRs, and convert IRs to exe.
        will return false if compilation failed
        ------
        pass_seq (list): optimization sequence
        '''
        exe=self.exe
        exe0=self.exe0
        oldexe='old-'+self.exe
        real_pass_seq=[]
        
        #复制初始IR
        cmds=[]
        for source in self.sources:
            reldir,filename=os.path.split(source)
            fileroot,fileext=os.path.splitext(filename)
            IR0=fileroot+'.bc'
            IR=fileroot+'.tmp.bc'
            cmd='cp {} {}'.format(IR0,IR)
            cmds.append(cmd)
        flag,ret = self._runcmd_parallel(cmds,cwd=self.build_dir)
        assert flag==True
        
        #若不使用任何pass进行优化
        if pass_seq==[]:
            flag=self._opt_compile_noreduce([],exe,llc_flag='-O3', suffix='.tmp.bc')
            if not flag:
                return False,None
            else:
                return True,[]
            # self.objs=[]
            # cmds=[]
            # for source in self.sources:
            #     reldir,filename=os.path.split(source)
            #     fileroot,fileext=os.path.splitext(filename)
            #     IR_opt=fileroot+'.tmp.bc'
            #     obj=fileroot+'.o'
            #     self.objs.append(obj)
            #     cmd='llc -O3 -filetype=obj {} -o {}'.format(IR_opt,obj)
            #     cmds.append(cmd)
            # flag,ret = self._runcmd_parallel(cmds,cwd=self.build_dir)
            # if not flag:
            #     return False,None
            
            # cmd='{} -O3 *.o -o {} {}'.format(self.cross_linker,exe0, self.lflags)
            # flag,ret = self._runcmd(cmd, cwd=self.build_dir)
            # if not flag:
            #     return False,None
            # else:
            #     return True,[]
        
        
        
        #复制初始exe
        flag,ret = self._runcmd('cp {} {}'.format(exe0,oldexe),cwd=self.build_dir)
        assert flag==True
        
        
        for p_str in pass_seq:
            p=[p_str]
            flag=self._opt_compile_noreduce(p,exe,llc_flag='-O0',suffix='.tmp.bc')
            if not flag:
                return False,None
            # cmds=[]
            # for source in self.sources:
            #     reldir,filename=os.path.split(source)
            #     fileroot,fileext=os.path.splitext(filename)
            #     IR=fileroot+'.tmp.bc'
            #     IR_opt=fileroot+'.opt.bc'
            #     cmd='opt {} {} -o {}'.format(p, IR,IR_opt)
            #     cmds.append(cmd)
            # flag,ret = self._runcmd_parallel(cmds,cwd=self.build_dir)
            # if not flag:
            #     return False,None
            
            # self.objs=[]
            # cmds=[]
            # for source in self.sources:
            #     reldir,filename=os.path.split(source)
            #     fileroot,fileext=os.path.splitext(filename)
            #     IR_opt=fileroot+'.opt.bc'
            #     obj=fileroot+'.o'
            #     self.objs.append(obj)
            #     cmd='llc -O3 -filetype=obj {} -o {}'.format(IR_opt,obj)
            #     cmds.append(cmd)
            # flag,ret = self._runcmd_parallel(cmds,cwd=self.build_dir)
            # if not flag:
            #     return False,None
            
            
            
            # cmd='{} -O3 *.o -o {} {}'.format(self.cross_linker,exe, self.lflags)
            # flag,ret = self._runcmd(cmd, cwd=self.build_dir,timeout=self.max_link_time)
            # if not flag:
            #     return False,None
            
            
            
            flag,ret = self._runcmd('diff {} {}'.format(exe, oldexe), cwd=self.build_dir)
            #如果该pass生效，保留该pass
            if ret.stdout.decode()!='':
                real_pass_seq.append(p_str)
                cmds=[]
                for source in self.sources:
                    reldir,filename=os.path.split(source)
                    fileroot,fileext=os.path.splitext(filename)
                    IR0=fileroot+'.opt.bc'
                    IR=fileroot+'.tmp.bc'
                    cmd='cp {} {}'.format(IR0,IR)
                    cmds.append(cmd)
                flag,ret = self._runcmd_parallel(cmds,cwd=self.build_dir)
                assert flag==True
                
            #复制exe
            flag,ret = self._runcmd('cp {} {}'.format(exe,oldexe),cwd=self.build_dir)
            assert flag==True
                
            
        self.objs=[]
        cmds=[]
        for source in self.sources:
            reldir,filename=os.path.split(source)
            fileroot,fileext=os.path.splitext(filename)
            IR_opt=fileroot+'.opt.bc'
            obj=fileroot+'.o'
            self.objs.append(obj)
            cmd='llc -O3 -filetype=obj {} -o {}'.format(IR_opt,obj)
            cmds.append(cmd)
        flag,ret = self._runcmd_parallel(cmds,cwd=self.build_dir)
        if not flag:
            return False,None
        
        cmd='{} -O3 {} -o {} {}'.format(self.cross_linker,' '.join(self.objs), exe, self.lflags)
        flag,ret = self._runcmd(cmd, cwd=self.build_dir,timeout=self.max_link_time)
        if not flag:
            return False,None
        
        return True,real_pass_seq
    
    def seq2ir2vec(self, pass_seq, tmp_dirname):
        pass_seq=' '.join(pass_seq)
        # if os.path.isdir(tmp_dirname):
        #     shutil.rmtree(tmp_dirname)
        # os.makedirs(tmp_dirname,exist_ok=True)
        for source in self.sources:
            reldir,filename=os.path.split(source)
            fileroot,fileext=os.path.splitext(filename)
            IR0=fileroot+'.bc'
            IR=os.path.join(tmp_dirname, IR0)
            cmd='cp {} {}'.format(IR0,IR)
            flag,ret = self._runcmd(cmd, cwd=self.build_dir,timeout=2.0)
            assert flag==True
            
        tmp_vec_file=os.path.join(tmp_dirname,'tmp_vec.txt')
        if os.path.isfile(tmp_vec_file):
            os.remove(tmp_vec_file)
            
        vec_file=os.path.join(tmp_dirname,'vec.txt')
        if os.path.isfile(vec_file):
            os.remove(vec_file)
            
        t0 = time.time()
        for source in self.sources:
            reldir,filename=os.path.split(source)
            fileroot,fileext=os.path.splitext(filename)
            IR=os.path.join(tmp_dirname, fileroot+'.bc')
            IR_opt=os.path.join(tmp_dirname, fileroot+'.opt.bc')
            cmd='opt {} {} -o {}'.format(pass_seq,IR,IR_opt)
            flag,ret = self._runcmd(cmd, cwd=self.build_dir,timeout=self.max_opt_time)
            assert flag==True,cmd
            if not flag:
                return
            
            # cmd='cp {} {}'.format(IR_opt,IR)
            # flag,ret = self._runcmd(cmd, cwd=self.build_dir,timeout=2.0)
            # assert flag==True, cmd
            
            # IR_opt_ll=os.path.join(tmp_dirname, fileroot+'.opt.ll') 
            # cmd='llvm-dis {} -o {}'.format(IR_opt,IR_opt_ll) 
            # flag,ret = self._runcmd(cmd, cwd=self.build_dir,timeout=2.0)
            # assert flag==True  
              
            lib='/home/jiayu/llvmtuner/IR2vec_prof/build/lib/libHelloWorld.so'
            cmd="opt -load-pass-plugin {} -passes=hello-world -disable-output {} 2>> {}".format(lib, IR_opt, tmp_vec_file)
            # vocab='/home/jiayu/llvmtuner/IR2Vec/vocabulary/seedEmbeddingVocab-300-llvm12.txt'
            # cmd='ir2vec -sym -vocab {} -o {} -level p {}'.format(vocab, tmp_vec_file, IR_opt)
            flag,ret = self._runcmd(cmd, cwd=self.build_dir,timeout=10.0)
            assert flag==True,cmd
        
        # print('time:',time.time()-t0)
        
        with open(tmp_vec_file,'r') as f:
            strs=f.readlines()
        assert len(strs) % len(self.sources) == 0
        vecs=[]
        for string in strs:
            str_list=string.strip().split('\t')
            vec = [float(val) for val in str_list]
            vecs.append(vec)
        
        
        chunked_vecs = []
        for i in range(0, len(vecs), len(self.sources)):
            vec=np.sum(vecs[i:i+len(self.sources)],axis=0).tolist()
            chunked_vecs.append(vec)
            with open(vec_file, "a") as f:
                f.write(json.dumps(vec) + '\n')
                
    # def ir2obj(self, ind, llc_flag='-O3'):
    #     cmds=[]
    #     self.objs=[]
    #     for source in self.sources:
    #         reldir,filename=os.path.split(source)
    #         fileroot,fileext=os.path.splitext(filename)
    #         tmp_dir=os.path.join(self.build_dir,'tmp{}'.format(ind))
    #         IR=os.path.join(tmp_dir,fileroot+'.opt.bc')
    #         obj=os.path.join(tmp_dir,fileroot+'.o')
    #         self.objs.append(obj)
    #         llc_cmd='llc {} -filetype=obj {} -o {}'.format(llc_flag, IR, obj)
    #         cmd=llc_cmd
    #         flag,ret = self._runcmd(cmd, cwd=self.build_dir)
    #         assert flag==True, cmd
    #         if not flag:
    #             return False
    #         cmds.append(cmd)
    #     # flag,ret = self._runcmd_parallel(cmds,cwd=self.build_dir)
    #     # if not flag:
    #     #     return False
        
    #     cmd='{} -O3 {} -o {} {}'.format(self.cross_linker,' '.join(self.objs), os.path.join(tmp_dir,self.exe), self.lflags)
    #     flag,ret = self._runcmd(cmd, cwd=self.build_dir)
    #     assert flag==True, cmd
    #     if not flag:
    #         return False
        
    #     cmd='cp {} {}'.format(os.path.join(tmp_dir,self.exe), self.exe)
    #     flag,ret = self._runcmd(cmd, cwd=self.build_dir)
    #     if not flag:
    #         return False
    #     return True
        
    
    
    
    

    def _runcmd(self,cmd,cwd=None,timeout=None):
        '''
        用于执行命令行cmd命令，如果命令执行出错或者超时则输出相应信息，
        这里接受的cmd是一个string,cwd是当前工作路径
        '''
        try:
            ret=subprocess.run(cmd, cwd=cwd, capture_output=True,shell=True,timeout=timeout)
            if ret.returncode == 0:
                flag=True
            else:
                flag=False
        except subprocess.TimeoutExpired:
            flag=False
            ret=None
        return flag, ret
    
    def adaptive_measure(self, max_num=32):
        '''
        自适应多次测量运行时间，通过置信区间控制测量次数
        若当前置信区间下界仍然大于最优结果，则没有必要继续测量
        max_num：最大测量次数
        tolerance：置信区间小于该容忍度时，认为测量足够准确
        '''
        exe=self.exe
        ret=subprocess.run('md5sum {}'.format(exe), cwd=self.build_dir, capture_output=True, shell=True)
        md5sum=ret.stdout.decode().split()[0]
        if md5sum in self.ms2y:
            print('Got the same binary')
            runtime=self.ms2y[md5sum]
            return runtime,[runtime]
        y=self.run()
        y_list=[y]
        if y < 1.1*self.best_y:
            for num in range(max_num):
                y=self.run()
                y_list.append(y)
                std=np.std(y_list)
                mean=np.mean(y_list)
                # if mean-std > self.best_y:
                #     break
                if mean < self.best_y:
                    if num>8 and std/mean<0.01:
                        break
                elif mean < 1.02*self.best_y:
                    if num>2 and std/mean<0.02:
                        break
                else: 
                    if num>0 and std/mean<0.03:
                        break
                    elif num>2:
                        break
                    
        
        y=np.mean(y_list)
        self.ms2y[md5sum]=y
        if y < self.best_y:
            self.best_y = y
        return y, y_list
    
    def _runcmd_parallel(self,cmds,cwd=None,timeout=None):
        '''
        用于并行执行命令行cmd命令，如果命令执行出错或者超时则输出相应信息，
        这里接受的cmd是一个string,cwd是当前工作路径
        '''
        chunked_cmds = []
        for i in range(0, len(cmds), self.n_parallel):
            chunked_cmds.append(cmds[i:i+self.n_parallel])
        
        for pcmds in chunked_cmds:
            procs = []
            for cmd in pcmds:
                procs.append(subprocess.Popen(cmd, cwd=cwd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            exit_codes = [p.wait() for p in procs]
        if not any(exit_codes):
            flag=True
        else:
            flag=False
        ret =None
        return flag,ret
    
    def reduce_inacative_pass(self, pass_seq):
        print('start reducing {}'.format(pass_seq))
        seq=deepcopy(pass_seq)
        oldexe='old-'+self.exe
        exe=self.exe
        self._opt_compile_noreduce(pass_seq, oldexe,suffix='.bc')
        change=False
        for i in range(len(pass_seq)):
            seq[i]=''
            seq0=[x for x in seq if x !='']
            self._opt_compile_noreduce(seq0, exe,suffix='.bc')
            flag,ret = self._runcmd('diff {} {}'.format(exe, oldexe), cwd=self.build_dir)
            if ret.stdout.decode()=='':
                change=True
            else:
                seq[i]=pass_seq[i]
                seq0=[x for x in seq if x !='']
            print(seq0,len(seq0))
    
    def reduce_pass(self, pass_seq):
        print('start reducing {}'.format(pass_seq))
        seq=deepcopy(pass_seq)
        y_ref=self.__call__(pass_seq)
        change=False
        for i in range(len(pass_seq)):
            seq[i]=''
            seq0=[x for x in seq if x !='']
            print(seq0,len(seq0))
            y=self.__call__(seq0)
            if y <= y_ref:
                y_ref=y
                change=True
            elif y > y_ref*1.01:
                seq[i]=pass_seq[i]
            else:
                change=True  
        seq0=[x for x in seq if x !='']
        if change==True:
            seq0, y_ref=self.reduce_pass(seq0)
        return seq0, y_ref
        
        
                    
    def __call__(self, pass_seq):
        '''
        
        ------
        x (array): a numerical input array which can be transformed to optimization sequence
        pass_seq (list): optimization sequence
        '''
        pass_seq
        if pass_seq in self.seqs:
            print('input the same sequence')
        else:
            self.seqs.append(pass_seq)
        # t0=time.time()
        # ret, real_pass_seq=self._opt_compile(pass_seq)
        # print('compile time:',time.time()-t0)
        ret=self._opt_compile_noreduce(pass_seq, self.exe, suffix='.bc')
        real_pass_seq=pass_seq
        self.pass_seq=real_pass_seq
        if ret:
            y, y_list = self.adaptive_measure()
        else:
            y=self.max_run_time
            y_list=[y]
        
        # print(real_pass_seq,len(real_pass_seq))
        
        if y < self.best_y:
            self.best_y = y
        speedup=self.O3_run_time/y
        print('speedup:{}'.format(speedup), 'time:{}'.format(y), y_list)
        self.tracker.track(real_pass_seq, -speedup)    
        return y
    

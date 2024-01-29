# -*- coding: utf-8 -*-
"""
Created on Tue Dec  6 17:53:52 2022

@author: jiayu
"""
import os
import subprocess
import json
import hashlib
from math import inf
import numpy as np
from scipy import stats
import time
import random
import shutil
from copy import deepcopy



class Function_wrap:
    def __init__(self, cmd, build_dir, tmp_dir, run_and_eval_fun, hotfiles=None, run_dir=None, is_genprofdata=False, profdata=None, repeat = 1, max_n_measure = 10, adaptive_measure = True):
        '''
        Parameters
        ----------
        cmd : string
            DESCRIPTION.
        build_dir: string
            where we run our original build command/script
        tmp_dir : string
            DESCRIPTION.
        run_and_eval_fun : function
            DESCRIPTION.
        '''
        self.cmd = cmd
        self.hotfiles = hotfiles
        self.build_dir =build_dir
        self.tmp_dir = tmp_dir
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.cfg_dir = os.path.join(self.tmp_dir, 'LLVMTuner-cfg/')
        os.makedirs(self.cfg_dir, exist_ok=True)
        self.is_genprofdata = is_genprofdata
        # self.run_cmd = run_cmd
        self.run_and_eval = run_and_eval_fun
        self.run_dir = run_dir
        self.profdata = profdata
        self.repeat = repeat
        self.max_n_measure=max_n_measure
        self.adaptive_measure=adaptive_measure
        self.results={}

        
        
        
        self.wrong_seqs = {} # for each file, there are wrong sequences
        self.wrong_params = [] # for the whole project, there are wrong params
        
        self.params=[]
        self.cfg_paths=[]
        self.y=[]
        self.md5sums=[]
        self.best_y=inf
        self.result_file = os.path.join(self.tmp_dir, 'result.json')
    
    # def run_and_eval(self):
    #     ret = subprocess.run('time ' + self.run_cmd, shell=True, cwd=self.run_dir, capture_output=True)
    #     if ret.returncode != 0:
    #         return inf
    #     else:
    #         temp=ret.stderr.decode('utf-8').strip()
    #         real=temp.split('\n')[-3]
    #         searchObj = re.search( r'real\s*(.*)m(.*)s.*', real)
    #         runtime = int(searchObj[1])*60+float(searchObj[2])
    #         return runtime 
    
    def gen_profdata(self):
        pass

    # def gen_profdata(self):
    #     cmd = 'export LLVM_PROFILE_FILE="default%p.profraw"'
    #     ret = subprocess.run(cmd, shell=True, capture_output=True)
    #     assert ret.returncode == 0

    #     y = self.run_and_eval()
    #     assert y != inf

    #     cmd = 'llvm-profdata merge *.profraw -o default.profdata'
    #     ret = subprocess.run(cmd, shell=True, capture_output=True, cwd =self.run_dir)
    #     assert ret.returncode == 0

    #     cmd = 'rm *.profraw'
    #     ret = subprocess.run(cmd, shell=True, capture_output=True, cwd =self.run_dir)
    #     assert ret.returncode == 0
        
    #     profdata=os.path.join(self.run_dir, 'default.profdata')
    #     return profdata
    
    def gen_optIR(self, params):
        cfg={}
        cfg['tmp_dir'] = self.tmp_dir
        cfg['params'] = params
        if self.hotfiles:
            cfg['hotfiles'] = self.hotfiles
        opt_cfg_json= os.path.join(self.cfg_dir, 'cfg-{}.json'.format( hashlib.md5(str(params).encode('utf-8')).hexdigest()) )
        with open(opt_cfg_json, 'w') as f:
            json.dump(cfg, f, indent=4)
        
        assert 'clangopt' in self.cmd
        if '"clangopt"' in self.cmd or "'clangopt'" in self.cmd:
            build_cmd = self.cmd.replace('clangopt', 'clangopt --gen-ir --opt-cfg-json={} --profdata={}'.format(opt_cfg_json, self.profdata))
        else:
            build_cmd = self.cmd.replace('clangopt', '"clangopt --gen-ir --opt-cfg-json={} --profdata={}"'.format(opt_cfg_json, self.profdata))
        
        ret = subprocess.run(build_cmd, shell=True, capture_output=True, cwd =self.build_dir)
        if ret.returncode != 0:
            print('cmd failed:',build_cmd)
            return False
        return True
    
    def build(self, params):
        cfg={}
        cfg['tmp_dir'] = self.tmp_dir
        cfg['params'] = params
        cfg['hotfiles'] = self.hotfiles
        opt_cfg_json= os.path.join(self.cfg_dir, 'cfg-{}.json'.format( hashlib.md5(str(params).encode('utf-8')).hexdigest()) )
        with open(opt_cfg_json, 'w') as f:
            json.dump(cfg, f, indent=4)
        
        assert 'clangopt' in self.cmd
        if '"clangopt"' in self.cmd or "'clangopt'" in self.cmd or self.cmd.startswith('clangopt'):
            if self.is_genprofdata:
                build_cmd = self.cmd.replace('clangopt', f'clangopt --opt-cfg-json={opt_cfg_json} --profdata={self.profdata} --instrument-ir')
            else:
                build_cmd = self.cmd.replace('clangopt', f'clangopt --opt-cfg-json={opt_cfg_json} --profdata={self.profdata}')            
        else:
            if self.is_genprofdata:
                build_cmd = self.cmd.replace('clangopt', f'"clangopt --opt-cfg-json={opt_cfg_json} --profdata={self.profdata} --instrument-ir"')
            else:
                build_cmd = self.cmd.replace('clangopt', f'"clangopt --opt-cfg-json={opt_cfg_json} --profdata={self.profdata}"')
        
        
        ret = subprocess.run(build_cmd, shell=True, capture_output=True, cwd =self.build_dir)
        if ret.returncode != 0:
            print('cmd failed:',build_cmd)
            return False
        return True
    
    def reduce_pass(self, pass_seq_str):
        pass_seq = pass_seq_str.split() 
        print(f'start reducing {pass_seq}')
        seq=deepcopy(pass_seq)
        y_ref=self.__call__(' '.join(pass_seq))
        change=False
        for i in range(len(pass_seq)):
            seq[i]=''
            seq0=[x for x in seq if x !='']
            
            y=self.__call__(' '.join(seq0))
            if y > self.best_y*1.007:
                seq[i]=pass_seq[i]
            else:
                print(' '.join(seq0),len(seq0))
                change=True  
                
        seq0=[x for x in seq if x !='']
        if change==True:
            seq0, y_ref=self.reduce_pass(' '.join(seq0))
        return seq0, y_ref
    
    
    def measure(self):
        y_list=[]
        y=self.run_and_eval()
        if y == inf: 
            return inf
        if y < 0.03: # y<0.03 means executation failed
            return -inf
        else:
            y_list.append(y)
            if self.adaptive_measure:
                if y>self.best_y*1.2:
                    print(y_list)
                    return y
                for _ in range(self.max_n_measure - 1):
                    y_list.append(self.run_and_eval())
                    y_mean=np.mean(y_list)
                    ci=stats.t.interval(0.95, len(y_list)-1, loc=y_mean, scale=stats.sem(y_list)+0.0003)
                    if (ci[1]-ci[0])/y_mean < 0.01 or ci[0]*1.005>self.best_y:
                        print(y_list)
                        return(y_mean)
                print(y_list)
                return(y_mean)
            else:
                for _ in range(self.repeat -1):
                    y_list.append(self.run_and_eval())
                y_mean=np.mean(y_list)
                print(y_list)
                return(y_mean)
    
    def __call__(self, params):
        t0 = time.time()
        if params in self.params:
            print('the same sequence')
            return self.y[self.params.index(params)]
        

        flag = self.build(params)
        print(f'time of building:',time.time()-t0)
        cfg_path = os.path.join(self.cfg_dir, 'cfg-{}.json'.format( hashlib.md5(str(params).encode('utf-8')).hexdigest()) )

        if self.is_genprofdata:
            profdata = self.gen_profdata()
            shutil.rmtree(self.cfg_dir)
            return profdata
        
        if flag:
            hashobj = hashlib.md5()
            if self.hotfiles is not None:
                for filename in self.hotfiles:
                    fileroot,fileext=os.path.splitext(filename)
                    if isinstance(params, (str)):
                        opt_str=params
                    else:
                        opt_str=params[fileroot]
                    IR_dir=os.path.join(self.tmp_dir, fileroot, 'IR-{}/'.format( hashlib.md5(opt_str.encode('utf-8')).hexdigest()))
                    IR_opt=os.path.join(IR_dir, fileroot+'.opt.bc')
                    with open(IR_opt, 'rb') as f:
                        hashobj.update(f.read())

                md5sum=hashobj.hexdigest()
            else:
                md5sum=random.random()
                
            if md5sum not in self.md5sums:
                y = self.measure()
                if y!=inf and y != -inf:
                    self.params.append(params)
                    self.y.append(y)
                    self.md5sums.append(md5sum)
                    self.best_params = self.params[np.argmin(self.y)]
                    self.best_y = min(self.y)
                    self.n_evals = len(self.y)
                    
                    print("{}) fbest = {:.4f} f_current = {:.4f}".format(self.n_evals, self.best_y, self.y[-1]))
                    
                    data = [cfg_path, y]
                    with open(self.result_file, 'a') as f:
                        f.write(json.dumps(data)+'\n')
                    
                    if len(self.y) % 20 ==0:
                        plot_file=os.path.join(self.tmp_dir, 'plot{}.json'.format(self.n_evals))
                        with open(plot_file, 'a') as f:
                            f.write(json.dumps(self.y)+'\n')
                        
                        
                        best_result_file = os.path.join(self.tmp_dir, 'best_result{}.json'.format(self.n_evals))
                        data = [self.best_params, self.best_y]
                        with open(best_result_file, 'a') as f:
                            f.write(json.dumps(data)+'\n')
                return y             
            else:
                print('the same IR')
                return self.y[self.md5sums.index(md5sum)]
                  
        else:
            return inf
    
    
        
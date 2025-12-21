# -*- coding: utf-8 -*-
import os
import subprocess
import json
import hashlib
from math import inf
import re
import numpy as np
from scipy import stats
import time
import random
import shutil
from copy import deepcopy
from multiprocessing import Pool
import llvmtuner
from llvmtuner.utils import get_func_names, run_and_eval, run_and_eval_ssh
from llvmtuner.searchspace import passlist2str, parse_O3string, split_by_parentheses
from llvmtuner.feature_extraction import read_optstats_from_cfgjson
from llvmtuner.show_features import dict_changes



class Function_wrap:
    def __init__(self, build_cmd, build_dir, tmp_dir, run_cmd, run_dir, hotfiles=None, binary=None, ssh_connection=None, run_and_eval_fun=None, timeout=1000, is_genprofdata=False, profdata=None, repeat = 1, max_n_measure = 5, adaptive_measure = True, wrong_exetime= 0.05):
        '''
        Parameters
        ----------
        build_cmd : string
            compile cmd.
        build_dir: string
            where we run our original build command/script
        tmp_dir : string
            DESCRIPTION.
        run_cmd : string
            run cmd.
        binary : string, optional
            exe binary after compilation, e.g. /home/usr/testbench/a.out.
        '''
        self.build_cmd = build_cmd
        self.hotfiles = hotfiles
        self.binary = binary
        self.build_dir =build_dir
        self.tmp_dir = tmp_dir
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.cfg_dir = os.path.join(self.tmp_dir, 'LLVMTuner-cfg/')
        os.makedirs(self.cfg_dir, exist_ok=True)
        self.is_genprofdata = is_genprofdata
        self.ssh_connection = ssh_connection
        self.run_dir = run_dir
        self.run_cmd = run_cmd
        if run_and_eval_fun is None:
            if self.ssh_connection:
                self.run_and_eval = run_and_eval_ssh(run_cmd, run_dir, binary, ssh_connection, timeout)
            else:
                self.run_and_eval = run_and_eval(run_cmd, run_dir, binary, timeout)
        else:
            self.run_and_eval = run_and_eval_fun
        self.profdata = profdata
        self.repeat = repeat
        self.max_n_measure=max_n_measure
        self.adaptive_measure=adaptive_measure
        self.results={}
        self.exe = ''
        self.objs = {}


        self.wrong_seqs = {} # for each file, there are wrong sequences
        self.wrong_params = [] # for the whole project, there are wrong params
        
        self.params_list=[]
        self.cfg_paths=[]
        self.y=[]
        self.md5sums=[]
        self.best_y=inf
        self.result_file = os.path.join(self.tmp_dir, 'result.json')
        self.wrong_exetime = wrong_exetime
        # module2funcnames= self._get_func_names()
        # print(module2funcnames)

        hotobjsrecord = os.path.join(self.tmp_dir, 'hot_objs.json')
        if os.path.isfile(hotobjsrecord):
            os.remove(hotobjsrecord)


    def _get_func_names(self):
        t0 = time.time()
        opt_str = 'default<O0>'
        flag = self.build(opt_str)
        assert flag
        print(f'time of generating IRs:',time.time()-t0)
        
        module2funcnames = {}
        fileroot_list = []
        IR_list = []
        for name in os.listdir(self.tmp_dir):
            if os.path.isdir(os.path.join(self.tmp_dir, name)) and name!='LLVMTuner-cfg':
                fileroot=name
                IR_dir=os.path.join(self.tmp_dir, fileroot, 'IR-{}/'.format( hashlib.md5(opt_str.encode('utf-8')).hexdigest()))
                IR=os.path.join(IR_dir, fileroot +'.opt.bc')
                IR_list.append(IR)
                fileroot_list.append(fileroot)
        # print(fileroot_list)
        # funcnames_list=[]
        # for IR in IR_list:
        #     funcname = get_func_names(IR)
        #     funcnames_list.append(funcname)
        with Pool() as p:
            funcnames_list = p.map(get_func_names, IR_list)

        module2funcnames = dict(zip(fileroot_list, funcnames_list))

        #以下用于处理头文件中含有函数定义，导致多个IR/obj文件中有相同函数名的情况
        with open(os.path.join(self.tmp_dir, 'link_cmd.json'),'r') as ff:
            link_cmd = json.load(ff)
        objs = re.findall(r'\b(\S+\.o)\b', link_cmd)
        # 记录已经出现的函数名
        seen_funcs = set()
        # 存储最终的 module2funcnames
        new_module2funcnames = {}
        # 遍历 objs 列表，按照顺序处理模块
        for obj in objs:
            fileroot = os.path.splitext(obj)[0]
            fileroot = fileroot.replace('/','_')
            if fileroot in module2funcnames:
                # 获取当前模块的函数名集合
                current_funcnames = module2funcnames[fileroot]
                # 过滤掉已经出现的函数名
                filtered_funcnames = {fn for fn in current_funcnames if fn not in seen_funcs}
                # 更新已出现的函数名集合
                seen_funcs.update(filtered_funcnames)
                # 更新新的 module2funcnames
                new_module2funcnames[fileroot] = filtered_funcnames
        module2funcnames = new_module2funcnames

        return module2funcnames



    
    
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
    
    @staticmethod
    def aaa(params):
        return len(params)

    def gen_optIR(self, params):
        cfg={}
        cfg['tmp_dir'] = self.tmp_dir
        cfg['params'] = params
        if self.hotfiles:
            cfg['hotfiles'] = self.hotfiles
        cfgpath= os.path.join(self.cfg_dir, 'cfg-{}.json'.format( hashlib.md5(str(params).encode('utf-8')).hexdigest()) )
        with open(cfgpath, 'w') as f:
            json.dump(cfg, f, indent=4)
        
        assert 'clangopt' in self.build_cmd or 'clangxxopt' in self.build_cmd
        build_cmd = self.build_cmd

        if '"clangopt' in build_cmd or "'clangopt" in build_cmd or build_cmd.startswith('clangopt'):
            build_cmd = build_cmd.replace('clangopt', 'clangopt --gen-ir --opt-cfg-json={} --profdata={}'.format(cfgpath, self.profdata))
        else:
            build_cmd = build_cmd.replace('clangopt', '"clangopt --gen-ir --opt-cfg-json={} --profdata={}"'.format(cfgpath, self.profdata))
        
        if '"clangxxopt' in build_cmd or "'clangxxopt" in build_cmd or build_cmd.startswith('clangxxopt'):
            build_cmd = build_cmd.replace('clangxxopt', 'clangxxopt --gen-ir --opt-cfg-json={} --profdata={}'.format(cfgpath, self.profdata))
        else:
            build_cmd = build_cmd.replace('clangxxopt', '"clangxxopt --gen-ir --opt-cfg-json={} --profdata={}"'.format(cfgpath, self.profdata))
        
        ret = subprocess.run(build_cmd, shell=True, capture_output=True, cwd =self.build_dir)
        if ret.returncode != 0:
            print('cmd failed:',build_cmd)
            return False
        return True
    
    @staticmethod
    def static_gen_optIR(inputs):
        params, tmp_dir, hotfiles, cmd, cfg_dir, build_dir, profdata = inputs
        cfg={}
        cfg['tmp_dir'] = tmp_dir
        cfg['params'] = params
        if hotfiles:
            cfg['hotfiles'] = hotfiles
        cfgpath= os.path.join(cfg_dir, 'cfg-{}.json'.format( hashlib.md5(str(params).encode('utf-8')).hexdigest()) )
        with open(cfgpath, 'w') as f:
            json.dump(cfg, f, indent=4)
        
        assert 'clangopt' in cmd or 'clangxxopt' in cmd
        build_cmd = cmd

        if '"clangopt' in build_cmd or "'clangopt" in build_cmd or build_cmd.startswith('clangopt'):
            build_cmd = build_cmd.replace('clangopt', 'clangopt --gen-ir --opt-cfg-json={} --profdata={}'.format(cfgpath, profdata))
        else:
            build_cmd = build_cmd.replace('clangopt', '"clangopt --gen-ir --opt-cfg-json={} --profdata={}"'.format(cfgpath, profdata))
        
        if '"clangxxopt' in build_cmd or "'clangxxopt" in build_cmd or build_cmd.startswith('clangxxopt'):
            build_cmd = build_cmd.replace('clangxxopt', 'clangxxopt --gen-ir --opt-cfg-json={} --profdata={}'.format(cfgpath, profdata))
        else:
            build_cmd = build_cmd.replace('clangxxopt', '"clangxxopt --gen-ir --opt-cfg-json={} --profdata={}"'.format(cfgpath, profdata))
        
        ret = subprocess.run(build_cmd, shell=True, capture_output=True, cwd =build_dir)
        if ret.returncode != 0:
            print('cmd failed:',build_cmd)
            return False
        return True

    def build(self, params):
        cfg={}
        cfg['tmp_dir'] = self.tmp_dir
        cfg['params'] = params
        if self.hotfiles:
            cfg['hotfiles'] = self.hotfiles
        else:
            cfg['hotfiles'] = None
        cfgpath= os.path.join(self.cfg_dir, 'cfg-{}.json'.format( hashlib.md5(str(params).encode('utf-8')).hexdigest()) )
        with open(cfgpath, 'w') as f:
            json.dump(cfg, f, indent=4)
        
        assert 'clangopt' in self.build_cmd or 'clangxxopt' in self.build_cmd
        build_cmd = self.build_cmd
        if '"clangopt' in build_cmd or "'clangopt" in build_cmd or build_cmd.startswith('clangopt'):
            if self.is_genprofdata:
                build_cmd = build_cmd.replace('clangopt', f'clangopt --opt-cfg-json={cfgpath} --profdata={self.profdata} --instrument-ir')
            else:
                build_cmd = build_cmd.replace('clangopt', f'clangopt --opt-cfg-json={cfgpath} --profdata={self.profdata}')            
        else:
            if self.is_genprofdata:
                build_cmd = build_cmd.replace('clangopt', f'"clangopt --opt-cfg-json={cfgpath} --profdata={self.profdata} --instrument-ir"')
            else:
                build_cmd = build_cmd.replace('clangopt', f'"clangopt --opt-cfg-json={cfgpath} --profdata={self.profdata}"')

        
        if '"clangxxopt' in build_cmd or "'clangxxopt" in build_cmd or build_cmd.startswith('clangxxopt'):
            if self.is_genprofdata:
                build_cmd = build_cmd.replace('clangxxopt', f'clangxxopt --opt-cfg-json={cfgpath} --profdata={self.profdata} --instrument-ir')
            else:
                build_cmd = build_cmd.replace('clangxxopt', f'clangxxopt --opt-cfg-json={cfgpath} --profdata={self.profdata}')            
        else:
            if self.is_genprofdata:
                build_cmd = build_cmd.replace('clangxxopt', f'"clangxxopt --opt-cfg-json={cfgpath} --profdata={self.profdata} --instrument-ir"')
            else:
                build_cmd = build_cmd.replace('clangxxopt', f'"clangxxopt --opt-cfg-json={cfgpath} --profdata={self.profdata}"')
        
        ret = subprocess.run(build_cmd, shell=True, capture_output=True, cwd =self.build_dir)
        if ret.returncode != 0:
            print('cmd failed:', build_cmd)
            return False
        #删除热点目标文件，以保证下次能重新编译
        with open(os.path.join(self.tmp_dir, 'hot_objs.json'),'r') as ff:
            for line in ff:
                obj_path = line.strip()
                if os.path.isfile(obj_path):
                    os.remove(obj_path)
        os.remove(os.path.join(self.tmp_dir, 'hot_objs.json'))
        return True
    
    def reduce_pass(self, params0):
        def reduce_pass_single(params1, fileroot):
            params=deepcopy(params1)
            y_ref=self.__call__(params)
            change=False
            opt_str = params[fileroot]
            pass_seq = parse_O3string(opt_str)
            seq=deepcopy(pass_seq)            
            for i in range(len(pass_seq)):
                seq[i]=''
                seq0=[x for x in seq if x !='']
                params[fileroot] = passlist2str(seq0)
                best = self.best_y
                best_params = self.best_params
                y=self.__call__(params)
                if y > best*1.01:
                    seq[i]=pass_seq[i]
                    pass_clear_name = split_by_parentheses(pass_seq[i])[-1].split('<')[0]
                    print(f'pass {pass_clear_name} is good for {fileroot}, from {y} to {best}')
                else:
                    print(fileroot,len(seq0))
                    change=True
                    if y*1.02 < best:
                        print(f'pass {pass_clear_name} is bad for {fileroot}, from {y} to {best}')
                        cfg0={}
                        cfg1={}
                        cfg0['params']=best_params 
                        cfg1['params']=params
                        cfg0['tmp_dir']=self.tmp_dir
                        cfg1['tmp_dir']=self.tmp_dir
                        cfg_json0=json.dumps(cfg0)
                        cfg_json1=json.dumps(cfg1)
                        features0 = read_optstats_from_cfgjson(cfg_json0)
                        features1 = read_optstats_from_cfgjson(cfg_json1)
                        changes = dict_changes(features0, features1)
                        for key in sorted(changes.keys()):
                            print(f"{key}: {changes[key]}")


            seq0=[x for x in seq if x !='']
            params[fileroot] = passlist2str(seq0)
            if change==True:
                print('====================================')
                print(f'restart reducing {fileroot}')
                params, y_ref=reduce_pass_single(params, fileroot)
            return params, y_ref

        for fileroot in self.hotfiles:
            # fileroot,fileext=os.path.splitext(filename)
            print(f'start reducing {fileroot}')
            params0, y_ref = reduce_pass_single(params0, fileroot)
        return params0, y_ref
    
    def measure(self):
        y_list=[]
        y=self.run_and_eval()
        if y == inf: 
            return inf
        if y < self.wrong_exetime: # y<wrong_exetime means executation failed
            return inf
        else:
            y_list.append(y)
            if self.adaptive_measure:
                if y>self.best_y*1.1:
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
    
    def run_and_getinfo(self):
        flag = self.build(params)
        assert flag
        

    def __call__(self, params):
        t0 = time.time()
        if params in self.params_list:
            print('the same sequence')
            return self.y[self.params_list.index(params)]


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
                for fileroot in self.hotfiles:
                    # fileroot,fileext=os.path.splitext(filename)
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
                t0 = time.time()
                y = self.measure()
                print(f'time of measuring:',time.time()-t0, y)
                t0 = time.time()
                if y!=inf and y != -inf:
                    self.params_list.append(deepcopy(params))
                    self.y.append(y)
                    self.md5sums.append(md5sum)
                    self.best_params = self.params_list[np.argmin(self.y)]
                    self.best_y = min(self.y)
                    self.n_evals = len(self.y)
                                        
                    data = [cfg_path, y]
                    with open(self.result_file, 'a') as f:
                        f.write(json.dumps(data)+'\n')
                    
                    if len(self.y) % 50 ==0:
                        plot_file=os.path.join(self.tmp_dir, 'plot{}.json'.format(self.n_evals))
                        with open(plot_file, 'a') as f:
                            f.write(json.dumps(self.y)+'\n')
                        
                        
                        best_result_file = os.path.join(self.tmp_dir, 'best_result{}.json'.format(self.n_evals))
                        data = [self.best_params, self.best_y]
                        with open(best_result_file, 'a') as f:
                            f.write(json.dumps(data)+'\n')
                    # print(f'time of saving results:',time.time()-t0)
                    print("{}) fbest = {:.4f} f_current = {:.4f}".format(self.n_evals, self.best_y, self.y[-1]))

                return y             
            else:
                print('the same IR')
                return self.y[self.md5sums.index(md5sum)]
                  
        else:
            return inf
    
    
        
from multiprocessing import Pool
import subprocess
import os
import json
import hashlib
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--cfgfile', required=True, help='')
args = parser.parse_args()

def square(x):
    return x * x

def gen_optIR(inputs):
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

if __name__ == "__main__":
    with open(args.cfgfile, 'r') as f:
        cfg = json.load(f)
    tmp_dir = cfg['tmp_dir']
    hotfiles = cfg['hotfiles']
    build_cmd = cfg['build_cmd']
    cfg_dir = cfg['cfg_dir']
    build_dir = cfg['build_dir']
    profdata = cfg['profdata']
    params_list = cfg['params_list']
    inputs = [(params, tmp_dir, hotfiles, build_cmd, cfg_dir, build_dir, profdata) for params in params_list]
    with Pool() as p:
        p.map(gen_optIR, inputs)
    
    # with Pool() as p:
    #     p.map(square, range(1000))

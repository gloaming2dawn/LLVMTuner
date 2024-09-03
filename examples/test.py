import llvmtuner
from llvmtuner.searchspace import default_space, passlist2str, parse_O3string

import os
import json
import hashlib
result_dir = '/home/jiayu/result_llvmtuner_17/cBench/security_sha/cost_model/result.json'
tmp_dir = '/home/jiayu/result_llvmtuner_17/cBench/security_sha/cost_model/'
fileroot = 'sha'
with open(result_dir, 'r') as file:
    for line in file:
        config_path, time = json.loads(line)
print(config_path, time)
with open(config_path, 'r') as file:
    config = json.load(file)
    opt_str=config['params'][fileroot]
hash_str = hashlib.md5(opt_str.encode('utf-8')).hexdigest()
IR_dir=os.path.join(tmp_dir, fileroot, f'IR-{hash_str}/')
print(IR_dir)
print(config)
# os.makedirs(IR_dir, exist_ok=True)




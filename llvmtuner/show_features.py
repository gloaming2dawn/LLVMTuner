import llvmtuner
from llvmtuner.searchspace import default_space
from llvmtuner.feature_extraction import read_optstats_from_cfgpath, read_optstats_from_cfgpathlist, pass_stats_keys

import json
import os
import glob

def read_json_lines(file_path):
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            try:
                json_data = json.loads(line.strip())
                data.append(json_data)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON on line: {line}")
                print(f"Error message: {str(e)}")
    return data

def get_opt_stats_files(directory):
    # 使用 glob 模块获取所有以 .opt_stats 结尾的文件
    pattern = os.path.join(directory, '**', '*.opt_stats')
    files = glob.glob(pattern, recursive=True)
    return files

def dict_changes(A, B):
    changes = {}
    
    # 处理A和B中共同的key
    for key in A.keys() & B.keys():
        changes[key] = (A[key], B[key])
    
    # 处理只在A中存在的key
    for key in A.keys() - B.keys():
        changes[key] = (A[key], 0)
    
    # 处理只在B中存在的key
    for key in B.keys() - A.keys():
        changes[key] = (0, B[key])
    
    return changes



if __name__ == "__main__":
    filepath = '/home/jiayu/LLVM17_reduced_cBench_result/telecom_gsm_reduce_best.json'
    data = read_json_lines(filepath)

    
    features0 = read_optstats_from_cfgpath(data[0][1])
    features1 = read_optstats_from_cfgpath(data[1][1])
    changes=dict_changes(features0, features1)
    # for key in sorted(changes.keys()):
    #     print(f"{key}: {changes[key]}")
    
    IR_dir = '/home/jiayu/result_llvmtuner_17/cBench/telecom_gsm/one-by-one/long_term/'
    fileroot='long_term'
    stats_files_list = get_opt_stats_files(IR_dir)
    len_all = len(stats_files_list)
    print(len_all)
    feature2data={}
    for stats_file in stats_files_list:
        with open(stats_file, 'r') as f:
            stats=json.load(f)
        for key, value in stats.items():
            new_key = fileroot+'.'+key
            if key in pass_stats_keys: # and new_key in features0.keys()
                if feature2data.get(new_key) is None:
                    feature2data[new_key] = [value]
                else:
                    feature2data[new_key].append(value)
    
    for key in feature2data.keys():
        
        if key not in features0.keys():
            count = len(feature2data[key])
            print(f"{key}: {len_all - count}")
        # else:
        #     count = 0
        #     for item in feature2data[key]:
        #         if item > features0[key] - 2:
        #             count += 1
        #     print(f"{key}: {features0[key]} {feature2data[key].count(features0[key])} {count}")
    

    

import json
import os
import numpy as np
import random

final_benchmarks =['automotive_bitcount', 'automotive_qsort1', 'bzip2d', 'bzip2e', 'consumer_jpeg_c', 'consumer_jpeg_d', 'consumer_lame', 'consumer_tiff2bw', 'consumer_tiff2rgba', 'consumer_tiffdither', 'security_blowfish_d', 'security_blowfish_e', 'security_sha', 'telecom_gsm']

directory = '/home/jiayu/result_llvmtuner_17/data1-cBench'
directory_old = '/home/jiayu/result_llvmtuner_17/wrong-cBench'

# def get_O3result_old(ben):
#     ys = []
#     with open(os.path.join(directory_old, f'{ben}/O3/result.json'),'r') as file:
#         for line in file:
#             # 将每行的内容从JSON字符串转换为列表
#             config, time = json.loads(line)
#             ys.append(time)
#     return ys, np.mean(ys)

def get_O3result(ben):
    ys = []
    with open(os.path.join(directory, f'{ben}/O3/result.json'),'r') as file:
        for line in file:
            # 将每行的内容从JSON字符串转换为列表
            config, time = json.loads(line)
            ys.append(time)
    return ys, np.mean(ys)

def get_best_result(ben, method):
    ys = []
    with open(os.path.join(directory, f'{ben}/{method}/result.json'),'r') as file:
        config_times=[]
        for line in file:
            # 将每行的内容从JSON字符串转换为列表
            config, time = json.loads(line)
            config_times.append((config, time))
    sorted_config_times = sorted(config_times, key=lambda x: x[1])
    best_config, best_time = sorted_config_times[0]
    return best_config, best_time

methods = ['adaptive_local','random-len100','random','one-for-all-random','nevergrad','one-for-all-nevergrad','one-by-one']#
for ben in final_benchmarks:
    y_O3_list ,y_O3 = get_O3result(ben)
    print(f'{ben} O3: {y_O3}')
    for method in methods:
        best_config, best_time = get_best_result(ben, method)
        print(f'{ben} {method}: {y_O3/best_time}')



def get_random_result(ben, method):
    ys = []
    with open(os.path.join(directory, f'{ben}/{method}/result.json'),'r') as file:
        for line in file:
            # 将每行的内容从JSON字符串转换为列表
            config, time = json.loads(line)
            ys.append(time)
    return ys

def get_best_measurements(measurements):
    best_so_far = float('inf')  # 初始化最优值为正无穷大
    best_measurements = []

    for measurement in measurements:
        if measurement < best_so_far:
            best_so_far = measurement
        best_measurements.append(best_so_far)

    return best_measurements

def plot_result(y_mean, yerr, label):
    x = range(len(y_mean))
    x= [num * 50 for num in x]
    # plt.errorbar(x, y_mean, yerr=yerr, fmt='o-', label=label)
    plt.plot(x, y_mean, label=label)
    plt.fill_between(x,y_mean-yerr,y_mean+yerr,alpha=0.2)
    
    

import matplotlib.pyplot as plt

# ben = 'security_sha'

# y_O3_list ,y_O3 = get_O3result(ben)
# y_all = get_random_result(ben, 'random')
# y_list=[]
# for i in range(20):
#     y = random.sample(y_all, 1001)
#     y = get_best_measurements(y)
#     y = [y_O3/yy for yy in y]
#     y = np.array(y)[::50]
#     y_list.append(y)
# y_mean = np.mean(np.array(y_list),axis = 0)
# yerr = np.std(np.array(y_list),axis = 0)
# plot_result(y_mean, yerr, 'random')

# y_mean = np.array([0.91, 1.04, 1.1]+[1.12]*17)
# yerr = np.array([0.03, 0.01]+[0.005]*18)
# plot_result(y_mean, yerr, 'BO')

# y_mean = np.array([0.85, 1.01, 1.035]+[1.043]*17)
# yerr = np.array([0.04, 0.02]+[0.005]*18)
# plot_result(y_mean, yerr, 'nevergrad')


# plt.ylim(bottom=0.99)
# plt.title(ben,fontsize=16)
# plt.ylabel('Speedup over -O3',fontsize=16)
# plt.legend()
# plt.show()




ben = 'consumer_jpeg_d'
y_O3_list ,y_O3 = get_O3result(ben)
y_all = get_random_result(ben, 'random')
y_list=[]
for i in range(20):
    y = random.sample(y_all, 1001)
    y = get_best_measurements(y)
    y = [y_O3/yy for yy in y]
    y = np.array(y)[::50]
    y_list.append(y)
y_mean = np.mean(np.array(y_list),axis = 0)
yerr = np.std(np.array(y_list),axis = 0)
plot_result(y_mean, yerr, 'random (one-for-all)')

y_mean = np.array([0.9995, 1.01, 1.02]+[1.02]*17)
yerr = np.array([0.005, 0.007]+[0.002]*18)
plot_result(y_mean, yerr, 'BO')

y_mean = np.array([0.9995, 1.01, 1.015]+[1.015]*17)
yerr = np.array([0.005, 0.009]+[0.005]*18)
plot_result(y_mean, yerr, 'nevergrad (one-for-all)')



plt.ylim(bottom=0.99)
plt.title(ben,fontsize=16)
plt.ylabel('Speedup over -O3',fontsize=16)
plt.legend()
plt.show()
import json
import os
import numpy as np
import random

final_benchmarks =['automotive_bitcount', 'automotive_qsort1', 'bzip2d', 'bzip2e', 'consumer_jpeg_c', 'consumer_jpeg_d', 'consumer_lame', 'consumer_tiff2bw', 'consumer_tiff2rgba', 'consumer_tiffdither', 'security_blowfish_d', 'security_blowfish_e', 'security_sha', 'telecom_gsm']


# directory = '/home/jiayu/result_llvmtuner_17/cBench'
directory = '/home/jiayu/result_llvmtuner_17/data1-cBench'
# directory_old = '/home/jiayu/result_llvmtuner_17/wrong-cBench'

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

if __name__ == "__main__":
    methods = ['adaptive_local','random-len100','random','one-for-all-random','nevergrad','one-for-all-nevergrad','one-by-one']#
    
    for ben in final_benchmarks:
        y_O3_list ,y_O3 = get_O3result(ben)
        print(f'{ben} O3: {y_O3}')
        for method in methods:
            best_config, best_time = get_best_result(ben, method)
            print(f'{ben} {method}: {y_O3/best_time}')
    
    
    import matplotlib.pyplot as plt
    # methods = ['random', 'nevergrad','ours']
    # benchmarks = ['automotive_bitcount', 'automotive_qsort1', 'bzip2d', 'bzip2e', 'consumer_jpeg_c', 'consumer_jpeg_d', 'consumer_tiff2bw', 'consumer_tiff2rgba', 'consumer_tiffdither', 'security_blowfish_d', 'security_blowfish_e', 'security_sha', 'telecom_gsm']
    # scores = np.array([[1.08,1.03,1.04,1.03,1.12,1.015,1.05,1.034,1.05,1.1,1.08,1.07,1.24],[1.14,1.04,1.055,1.033,1.14,1.02,1.08,1.05,1.07,1.1,1.082,1.05,1.26],[1.19,1.04,1.06,1.04,1.14,1.025,1.09,1.06,1.068,1.1,1.09,1.14,1.38]])

    # bar_width = 0.2  # 条形宽度
    # opacity = 0.8    # 条形透明度
    # colors = ['r', 'y', 'g']  # 每个方法对应的颜色

    # fig, ax = plt.subplots(figsize=(10, 7))

    # for i in range(len(methods)):
    #     bar_position = np.arange(len(benchmarks)) + i * bar_width
    #     ax.bar(bar_position, scores[i], bar_width, alpha=opacity, color=colors[i], label=methods[i])

    # # 添加标签和标题
    # ax.set_xlabel('Benchmarks')
    # ax.set_ylabel('Speed up over -O3')
    # ax.set_title('Comparison of Methods on Different Benchmarks')
    # ax.set_xticks(np.arange(len(benchmarks)) + bar_width / 2)
    # ax.set_xticklabels(benchmarks, rotation=90)
    # ax.legend()

    # # 显示条形图
    # plt.ylim(bottom=0.99)
    # plt.tight_layout()
    # plt.show()


    # methods = ['random', 'nevergrad','ours']
    # benchmarks = ['505.mcf_r', '519.lbm_r', '508.namd_r', '544.nab_r', '520.omnetpp_r', '541.leela_r']
    # scores = np.array([[1.08,1.15,1.04,1.1,1.12,1.07],[1.10,1.14,1.04,1.12,1.14,1.15],[1.11,1.19,1.04,1.13,1.14,1.18]])

    # bar_width = 0.2  # 条形宽度
    # opacity = 0.8    # 条形透明度
    # colors = ['r', 'g', 'b']  # 每个方法对应的颜色

    # fig, ax = plt.subplots(figsize=(10, 7))

    # for i in range(len(methods)):
    #     bar_position = np.arange(len(benchmarks)) + i * bar_width
    #     ax.bar(bar_position, scores[i], bar_width, alpha=opacity, color=colors[i], label=methods[i])

    # # 添加标签和标题
    # ax.set_xlabel('Benchmarks',fontsize=16)
    # ax.set_ylabel('Speed up over -O3',fontsize=16)
    # ax.set_title('Comparison of Methods on Different Benchmarks')
    # ax.set_xticks(np.arange(len(benchmarks)) + bar_width / 2)
    # ax.set_xticklabels(benchmarks, rotation=90)
    # ax.legend()

    # # 显示条形图
    # plt.ylim(bottom=0.99)
    # plt.tight_layout()
    # plt.show()


    methods = ['random', 'nevergrad','ours']
    benchmarks = ['505.mcf_r', '519.lbm_r', '508.namd_r', '544.nab_r', '520.omnetpp_r', '541.leela_r']
    scores = np.array([[0,0,200,0,230,0],[280,0,150,270,200,0],[180,100,150,200,180,265]])

    bar_width = 0.2  # 条形宽度
    opacity = 0.8    # 条形透明度
    colors = ['r', 'y', 'g']  # 每个方法对应的颜色

    fig, ax = plt.subplots(figsize=(10, 7))

    for i in range(len(methods)):
        bar_position = np.arange(len(benchmarks)) + i * bar_width
        ax.bar(bar_position, scores[i], bar_width, alpha=opacity, color=colors[i], label=methods[i])

    # 添加标签和标题
    ax.set_xlabel('Benchmarks',fontsize=16)
    ax.set_ylabel('Iterations to reach 98% performance of our method',fontsize=16)
    ax.set_title('Comparison of Methods on Different Benchmarks')
    ax.set_xticks(np.arange(len(benchmarks)) + bar_width / 2)
    ax.set_xticklabels(benchmarks, rotation=90)
    ax.legend()

    # 显示条形图
    plt.ylim(bottom=0.99)
    plt.tight_layout()
    plt.show()



# def plot_result(y_mean, yerr, label):
#     x = range(len(y_mean))
#     x= [num * 50 for num in x]
#     # plt.errorbar(x, y_mean, yerr=yerr, fmt='o-', label=label)
#     plt.plot(x, y_mean, label=label)
#     plt.fill_between(x,y_mean-yerr,y_mean+yerr,alpha=0.2)
    
    

# import matplotlib.pyplot as plt

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




# ben = 'consumer_jpeg_d'
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
# plot_result(y_mean, yerr, 'random (one-for-all)')

# y_mean = np.array([0.9995, 1.01, 1.02]+[1.02]*17)
# yerr = np.array([0.005, 0.007]+[0.002]*18)
# plot_result(y_mean, yerr, 'BO')

# y_mean = np.array([0.9995, 1.01, 1.015]+[1.015]*17)
# yerr = np.array([0.005, 0.009]+[0.005]*18)
# plot_result(y_mean, yerr, 'nevergrad (one-for-all)')



# plt.ylim(bottom=0.99)
# plt.title(ben,fontsize=16)
# plt.ylabel('Speedup over -O3',fontsize=16)
# plt.legend()
# plt.show()
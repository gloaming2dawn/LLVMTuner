import llvmtuner
from llvmtuner.searchspace import default_space, passlist2str, parse_O3string
from llvmtuner.BO.BO import BO
from llvmtuner.BO.Adalocaloptimizer import Adalocaloptimizer

import json

# 待写入的数据
data = {
    'name': 'John',
    'age': 30,
    'city': 'New York'
}

# 文件路径
file = 'example.json'
datas = [data,data]
# 以追加模式打开文件，并写入JSON数据
for data in datas:
    with open(file, 'a') as ff:
        json.dump(data, ff, indent=4)
        # ff.write('\n')  # 追加换行符，以便下次写入时数据格式清晰分隔


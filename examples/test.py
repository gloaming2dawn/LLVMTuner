import re

# 示例链接命令
link_commands = [
    'clang -o outputfile target1.o target2.o',
    'clang -flag target1.o target2.o -o outputfile',
    'clang -o my_output_file long_option -o another_output target3.o',
    'clang -o outputfile -someflag -otherflag target1.o target2.o',
    'clang -o outputfile -someflag -otherflag target2.o target1.o -o outputfile.out a.cpp'
]

# 正则表达式匹配目标文件
def extract_object_files(command):
    # 提取 -o 标志之前的所有 .o 文件
    # 先匹配目标文件
    matches = re.findall(r'\b(\S+\.o)\b', command)
    return matches

# 处理所有示例链接命令
for command in link_commands:
    object_files = extract_object_files(command)
    print(f'Command: {command}')
    print(f'Object Files: {object_files}')
    print('---')

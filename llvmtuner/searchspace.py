# -*- coding: utf-8 -*-
"""
Created on Fri Feb 11 00:12:22 2022

@author: jiayu
"""
import time
import subprocess
import os
import re
import json
from copy import deepcopy

def parse_O3string(s, operator=None):
    result = []
    i = 0
    current = ""
    while i < len(s):
        if s[i] == ',':
            if current:
                result.append(current)
                current = ""
            i += 1
            continue
        elif s[i] == '(':
            # Find the matching closing parenthesis
            open_paren = 1
            start = i
            while i < len(s) - 1 and open_paren != 0:
                i += 1
                if s[i] == '(':
                    open_paren += 1
                elif s[i] == ')':
                    open_paren -= 1
            # Process the content within the parentheses
            nested_result = parse_O3string(s[start + 1:i], current)
            # result.extend(nested_result)
            for item in nested_result:
                result.append(f"{current}({item})")
            current = ""
        else:
            current += s[i]
        i += 1
    # Add any remaining elements
    if current:
        result.append(current)
    return result

def split_by_parentheses(s):
    stack = []  # 用于追踪圆括号
    result = []  # 最终结果列表
    current = []  # 当前处理的字符集合

    for char in s:
        if char == '(':
            if current:  # 当前字符集合非空时，加入结果列表
                result.append(''.join(current))
                current = []  # 重置当前字符集合
            stack.append('(')  # 开启新的圆括号
        elif char == ')':
            if stack:
                stack.pop()  # 移除匹配的开启圆括号
                if not stack:  # 如果堆栈为空，说明当前圆括号闭合
                    result.append(''.join(current))
                    current = []  # 重置当前字符集合
            else:  # 无匹配的开启圆括号，直接添加字符
                current.append(char)
        else:
            current.append(char)

    # 添加最后一段字符，如果有的话
    if current:
        result.append(''.join(current))

    return result


def parse_nested_string(s):
    """解析嵌套的字符串为结构化列表"""
    stack = [[]]
    current = ""
    for char in s:
        if char == '(':
            if current:
                stack[-1].append(current)
                current = ""
            stack.append([])
        elif char == ')':
            if current:
                stack[-1].append(current)
                current = ""
            nested = stack.pop()
            stack[-1].append(nested)
        else:
            current += char
    if current:
        stack[-1].append(current)
    return stack[0]

def build_nested_string(items):
    
    assert isinstance(items, list)
    if len(items) == 1:
        if isinstance(items[0], str):
            return(items[0])
        else:
            assert isinstance(items[0], list)
            nested = build_nested_string(items[0])
            return(nested)
    else:
        if isinstance(items[0], str):
            assert len(items) == 2
            assert isinstance(items[1], list)
            nested = build_nested_string(items[1])
            return(f"{items[0]}({nested})") # 加上圆括号表示嵌套
        else:
            result = []
            for item in items:
                assert isinstance(item, list)
                result.append(build_nested_string(item))
            return ','.join(result)


def merge_nested_lists(a, b):
    """合并结构化列表"""
    assert len(b)<3 and not isinstance(b[0], list)
    if isinstance(a[0], list):
        return a[:-1]+ merge_nested_lists(a[-1], b)
    elif len(a) == 1 or len(b) == 1 or a[0]!=b[0]:
        return [a, b]
    else:
        assert len(a) == 2
        return [[a[0],merge_nested_lists(a[1], b[1])]]
    

def check_seq(seq0):
    seq = deepcopy(seq0)
    #只允许一个cg-profile出现   
    cgprofile_count = 0
    for i in range(len(seq) - 1, -1, -1):
        pass0_name = split_by_parentheses(seq[i])[-1]
        if pass0_name == 'cg-profile':
            cgprofile_count += 1
        if cgprofile_count > 1:
            seq[i] = ''
            cgprofile_count -= 1

    seq = [s for s in seq if s != '']

    #不允许连续重复pass  
    for i in range(len(seq) - 1):
        pass0_name = split_by_parentheses(seq[i])[-1]
        pass1_name = split_by_parentheses(seq[i+1])[-1]
        if pass0_name == pass1_name:
            seq[i] = ''
    seq = [s for s in seq if s != '']
    return seq

def passlist2str(seq):
    seq = check_seq(seq)
    sa = parse_nested_string(seq[0])
    for i in range(len(seq)-1):
        sa = merge_nested_lists(sa, parse_nested_string(seq[i+1]))
    result = build_nested_string(sa)
    return result

def gen_kind2pass(filename):
    with open(filename, 'r') as file:
        content_dict = {}
        current_key = None
        for line in file:
            stripped_line = line.strip()
            # 如果行是空的，就跳过
            if not stripped_line:
                continue
            # 检查行是否有缩进
            if line[0].isspace():
                # 如果当前键不是None，将缩进的行添加到对应的键下
                if current_key is not None:
                    content_dict[current_key].append(stripped_line.split('<')[0])
            else:
                # 这行没有缩进，是一个新的键
                current_key = stripped_line
                content_dict[current_key] = []
    return content_dict



def default_space():
    cmd ='llvm-as < /dev/null | opt -O3 -disable-output --print-pipeline-passes > O3_debug_passes.txt'
    subprocess.run(cmd, shell=True)
    with open('O3_debug_passes.txt', 'r') as f:
        O3_string=f.read()
    O3_seq = parse_O3string(O3_string)
    result = passlist2str(O3_seq)
    # print(result == O3_string)

    # print('='*20)
    # print(json.dumps(O3_seq, indent=2))
    

    # O3_seq = re.split(r'[,()]', string.strip())
    # O3_seq = [x for x in O3_seq if x!='' and x!='function' and x!='cgscc' and x!='loop' and not x.startswith(('function<','loop<','cgscc<','devirt')) ]
    
    cmd ='opt --print-passes > all_passes.txt'
    subprocess.run(cmd, shell=True)
    kind2passes = gen_kind2pass('all_passes.txt')
    # print('='*20)
    # print('kind2passes', kind2passes)

    pass2kind = {}
    analysis_passes = []
    all_tran_passes = []
    for kind in kind2passes:
        if 'analyses' in kind:
            analysis_passes.extend(kind2passes[kind])
        else:
            for pass_ in kind2passes[kind]:
                if pass_.startswith(('print','view','verify')) or 'remark' in pass_ or 'invalidate' in pass_ or 'transform-warning' in pass_ or pass_ == 'recompute-globalsaa':
                    analysis_passes.append(pass_)
                else:
                    all_tran_passes.append(pass_)
                    if kind.startswith('Module'):
                        large_kind='module'
                    elif kind.startswith('CGSCC'):
                        large_kind='cgscc'
                    elif kind.startswith('Function'):
                        large_kind='function'
                    elif kind.startswith('Loop'):
                        large_kind='loop'
                    else:
                        assert 1==0
                    pass2kind[pass_] = large_kind

    # print('Number of all transform passes:',len(all_tran_passes))

    # for x in O3_seq:
    #     if x.split('<')[0] not in all_tran_passes:
    #         print(x)
    # O3_trans_seq=[x for x in O3_seq if x.split('<')[0] not in analysis_passes and x.split('<')[0] in all_tran_passes]# 
    # # print('O3 seq:',O3_trans_seq)

    O3_trans_seq=[x for x in O3_seq if split_by_parentheses(x)[-1].split('<')[0] in all_tran_passes]# 

    # print('Length of O3 seq:',len(O3_trans_seq))
    O3_passes = sorted(set(O3_trans_seq))
    # print('Number of O3 transform passes:',len(O3_passes))
    # print('O3 passes:',O3_passes)
    O3_passes_clear = [split_by_parentheses(x)[-1].split('<')[0] for x in O3_passes]
    O3_passes_clear = sorted(set(O3_passes_clear))
    # print('Number of clear O3 transform passes:',len(O3_passes_clear))
    # print('O3 passes clear:',O3_passes_clear)

    other_passes_clear = 'break-crit-edges loop-data-prefetch loop-fusion loop-interchange loop-unroll-and-jam lowerinvoke sink ee-instrument'.split() #loop-reduce 
    # other_passes_clear='loop-fusion'.split()
    other_passes_clear = [x for x in other_passes_clear if x not in O3_passes_clear]
    passes_clear = O3_passes_clear + other_passes_clear
    # print(passes_clear)

    other_passes =[]
    for pass_ in other_passes_clear:
        if pass2kind[pass_] == 'module':
            other_passes.append(pass_)
        elif pass2kind[pass_] == 'cgscc':
            other_passes.append(f'cgscc(devirt<4>({pass_})')
        elif pass2kind[pass_] == 'function':
            other_passes.append(f'function<eager-inv>({pass_})')
        elif pass2kind[pass_] == 'loop':
            other_passes.append(f'function<eager-inv>(loop({pass_}))')
    # print(other_passes)
    # other_passes =[]
    passes=sorted(list(set(O3_passes + other_passes)))
    print('Number of used passes:',len(passes))

    

    return passes, passes_clear, pass2kind, O3_trans_seq
    

if __name__ == "__main__":
    passes, passes_clear, pass2kind, O3_trans_seq = default_space()
    # print(len(passes))
    # print(passes)
    # print(pass2kind)
    


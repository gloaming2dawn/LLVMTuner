# -*- coding: utf-8 -*-
"""
Created on Mon Nov 14 23:23:10 2022

@author: jiayu
"""

def _init():  
    global _global_dict
    _global_dict = {}
    

def set_value(key, value):
    _global_dict[key] = value

def get_value(key):
    return _global_dict[key]


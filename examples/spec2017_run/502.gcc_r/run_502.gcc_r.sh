#!/bin/bash

# specinvoke r4356
#  Invoked as: specinvoke -n
# timer ticks over every 1000 ns
# Use another -n on the command line to see chdir commands and env dump
# Starting run for copy #0
./cpugcc_r_base.llvmtuner17.0.6 200.c -O3 -finline-limit=50000 -o 200.opts-O3_-finline-limit_50000.s > 200.opts-O3_-finline-limit_50000.out 2>> 200.opts-O3_-finline-limit_50000.err
# Starting run for copy #0
./cpugcc_r_base.llvmtuner17.0.6 scilab.c -O3 -finline-limit=50000 -o scilab.opts-O3_-finline-limit_50000.s > scilab.opts-O3_-finline-limit_50000.out 2>> scilab.opts-O3_-finline-limit_50000.err
# Starting run for copy #0
./cpugcc_r_base.llvmtuner17.0.6 train01.c -O3 -finline-limit=50000 -o train01.opts-O3_-finline-limit_50000.s > train01.opts-O3_-finline-limit_50000.out 2>> train01.opts-O3_-finline-limit_50000.err
#!/bin/bash

# specinvoke r4356
#  Invoked as: specinvoke -n
# timer ticks over every 1000 ns
# Use another -n on the command line to see chdir commands and env dump
# Starting run for copy #0
./namd_r_base.llvmtuner17.0.6 --input apoa1.input --iterations 7 --output apoa1.train.output > namd.out 2>> namd.err
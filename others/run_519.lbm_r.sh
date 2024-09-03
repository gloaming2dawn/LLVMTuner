#!/bin/bash

# specinvoke r4356
#  Invoked as: specinvoke -n
# timer ticks over every 1000 ns
# Use another -n on the command line to see chdir commands and env dump
# Starting run for copy #0
./lbm_r_base.llvmtuner17.0.6 300 reference.dat 0 1 100_100_130_cf_b.of > lbm.out 2>> lbm.err
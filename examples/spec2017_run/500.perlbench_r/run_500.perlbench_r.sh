#!/bin/bash

# specinvoke r4356
#  Invoked as: specinvoke -n
# timer ticks over every 1000 ns
# Use another -n on the command line to see chdir commands and env dump
# Starting run for copy #0
./perlbench_r_base.llvmtuner17.0.6 -I./lib diffmail.pl 2 550 15 24 23 100 > diffmail.2.550.15.24.23.100.out 2>> diffmail.2.550.15.24.23.100.err
# Starting run for copy #0
./perlbench_r_base.llvmtuner17.0.6 -I./lib perfect.pl b 3 > perfect.b.3.out 2>> perfect.b.3.err
# Starting run for copy #0
./perlbench_r_base.llvmtuner17.0.6 -I. -I./lib scrabbl.pl < scrabbl.in > scrabbl.out 2>> scrabbl.err
# Starting run for copy #0
./perlbench_r_base.llvmtuner17.0.6 -I./lib splitmail.pl 535 13 25 24 1091 1 > splitmail.535.13.25.24.1091.1.out 2>> splitmail.535.13.25.24.1091.1.err
# Starting run for copy #0
./perlbench_r_base.llvmtuner17.0.6 -I. -I./lib suns.pl > suns.out 2>> suns.err
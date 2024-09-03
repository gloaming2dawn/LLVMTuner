import subprocess

source_file = 'test.c'
IR = 'test.ll'
IR_opt = 'test_opt.ll'
opt_params = 'loop-simplify'
opt_params = 'default<O3>'
seq0 = ['cgscc(devirt<4>(function<eager-inv;no-rerun>(early-cse<memssa>)))', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(instcombine<max-iterations=1000;no-use-loop-info>)))', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(loop-mssa(loop-rotate<header-duplication;no-prepare-for-lto>))))', 'function<eager-inv>(loop-fusion)', 'sroa']
seq0 = ['cgscc(devirt<4>(function<eager-inv;no-rerun>(early-cse<memssa>)))', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(instcombine<max-iterations=1000;no-use-loop-info>)))', 'cgscc(devirt<4>(function<eager-inv;no-rerun>(loop-mssa(loop-rotate<header-duplication;no-prepare-for-lto>))))']#,'mem2reg','function<eager-inv>(loop-fusion)'
opt_params = ','.join(seq0)
opt_params = 'default<O3>'
cmd = f'clang -emit-llvm -S -O3 -Xclang -disable-llvm-optzns {source_file} -o {IR}'
subprocess.run(cmd, shell=True)
print(cmd)
cmd = f'opt -passes="{opt_params}" --print-before-changed {IR} -pass-remarks-missed=loop-fusion -S -o {IR_opt} -stats -stats-json'
print(cmd)
subprocess.run(cmd, shell=True)
cmd = f'clang {IR_opt} -O3'
subprocess.run(cmd, shell=True)
cmd = f'./a.out'
subprocess.run(cmd, shell=True)
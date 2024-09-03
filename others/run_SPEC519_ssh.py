import os
from fabric import Connection
import llvmtuner
from llvmtuner.function_wrap import Function_wrap
from llvmtuner.utils import run_and_eval, run_and_eval_ssh, perf_record, gen_hotfiles
from llvmtuner.BO.BO import BO
from llvmtuner.baselines.random import random_optimizer

ssh_connection=Connection(host="nvidia@TX2-1.local")

user_home = os.path.expanduser("~")
passes = llvmtuner.searchspace.default_space()[0]
benchmark = '519.lbm_r'
build_cmd = f'runcpu --action build --size train --config my-clang-linux-x86.cfg --define SPECLANG="clangopt" --define SPECLANGXX="clangxxopt" {benchmark}'
build_dir = f'{user_home}/cpu2017/benchspec/CPU/{benchmark}/exe/'
run_cmd = f'./run_{benchmark}.sh'
run_dir = f'/home/nvidia/spec2017_run/{benchmark}'
run_and_eval_fun = run_and_eval_ssh(run_cmd, run_dir)
tmp_dir = f'{user_home}/result_llvmtuner_17/SPEC/{benchmark}/random' #存放结果及中间文件
fun = Function_wrap(build_cmd, build_dir, tmp_dir, run_and_eval_fun)

optimizer=random_optimizer(
    fun=fun,
    passes=passes,
    len_seq=150,
    budget=1000, 
    )

optimizer.minimize()

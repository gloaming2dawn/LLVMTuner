import subprocess
import time

t1=time.time()
epochs=1
for i in range(epochs):
    cmd = f'python run_cBench_ssh.py --device=6 --method=nevergrad --benchmark=telecom_gsm --budget=1000'
    subprocess.run(cmd, shell=True)
    cmd = f'python run_cBench_ssh.py --device=6 --method=random-len80 --benchmark=security_sha --budget=5000'
    subprocess.run(cmd, shell=True)

    cmd = f'python run_cBench_ssh.py --device=6 --method=nevergrad --benchmark=telecom_gsm --budget=1000'
    subprocess.run(cmd, shell=True)

    cmd = f'python run_cBench_ssh.py --device=6 --method=random-len100 --benchmark=security_sha --budget=5000'
    subprocess.run(cmd, shell=True)

print('total time:',time.time()-t1)
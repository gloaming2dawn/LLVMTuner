import subprocess
import os
from fabric import Connection

# download cbench code
home_path = os.path.expanduser("~")
cbench_path = os.path.join(home_path, 'cBench_V1.1')
os.makedirs(cbench_path, exist_ok=True)
cmd = f'wget https://sourceforge.net/projects/cbenchmark/files/cBench/V1.1/cBench_V1.1.tar.gz'
subprocess.run(cmd, cwd = cbench_path, shell=True)
subprocess.run(f'tar -xvf cBench_V1.1.tar.gz', cwd = cbench_path, shell=True)
# create work directories
subprocess.run(f'./all__create_work_dirs', cwd = cbench_path, shell=True) 


# download cbench dataset
# files = ['cDatasets_V1.1_consumer_tiff_data.tar.gz','cDatasets_V1.1_office_data.tar.gz','cDatasets_V1.1_consumer_jpeg_data.tar.gz','cDatasets_V1.1_telecom_gsm_data.tar.gz','cDatasets_V1.1_consumer_data.tar.gz','cDatasets_V1.1_bzip2_data.tar.gz','cDatasets_V1.1_network_patricia_data.tar.gz','cDatasets_V1.1_network_dijkstra_data.tar.gz','cDatasets_V1.1_automotive_susan_data.tar.gz','cDatasets_V1.1_automotive_qsort_data.tar.gz']#,'cDatasets_V1.1_telecom_data.tar.gz'
files = ['cDatasets_V1.1_telecom_data.tar.gz']

for file in files:
    # cmd = f'wget https://sourceforge.net/projects/cbenchmark/files/cDatasets/V1.1/{file}'
    # subprocess.run(cmd, cwd = cbench_path, shell=True)
    # subprocess.run(f'tar -xvf {file}', cwd = cbench_path, shell=True)

# os.chmod(cbench_path, 0o755)
    

    for device in ['2','3','4','5','6']:#
        cmd = f'scp {file} nvidia@TX2-{device}.local:/home/nvidia/cBench_V1.1/'
        subprocess.run(cmd, cwd =cbench_path, shell=True)
        host=f"nvidia@TX2-{device}.local"
        sshC=Connection(host=host)
        with sshC.cd('/home/nvidia/cBench_V1.1/'):
            result = sshC.run(f'tar -xvf {file}', warn=True)
        if result.failed:
            print("Command failed, but we are continuing...")



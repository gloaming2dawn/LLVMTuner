import subprocess
from fabric import Connection

cwd = '/home/jiayu/cBench_V1.1/'
files = ['cDatasets_V1.1_consumer_tiff_data.tar.gz','cDatasets_V1.1_office_data.tar.gz','cDatasets_V1.1_telecom_data.tar.gz','cDatasets_V1.1_consumer_jpeg_data.tar.gz','cDatasets_V1.1_telecom_gsm_data.tar.gz','cDatasets_V1.1_consumer_data.tar.gz','cDatasets_V1.1_bzip2_data.tar.gz','cDatasets_V1.1_network_patricia_data.tar.gz','cDatasets_V1.1_network_dijkstra_data.tar.gz','cDatasets_V1.1_automotive_susan_data.tar.gz','cDatasets_V1.1_automotive_qsort_data.tar.gz']
for file in files:
    # cmd = f'wget https://sourceforge.net/projects/cbenchmark/files/cDatasets/V1.1/{file}'
    # subprocess.run(cmd, cwd =cwd, shell=True)

    for device in ['4']:#'1','3','4','5','6'
        cmd = f'scp {file} nvidia@TX2-{device}.local:/home/nvidia/cBench_V1.1/'
        subprocess.run(cmd, cwd =cwd, shell=True)
        host=f"nvidia@TX2-{device}.local"
        sshC=Connection(host=host)
        with sshC.cd('/home/nvidia/cBench_V1.1/'):
            sshC.run(f'tar -xvf {file}')



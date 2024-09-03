from fabric import Connection

# 远程主机连接信息
ssh_connection=Connection(host=f'nvidia@TX2-6.local')

# 远程文件路径
remote_file_path = '/home/nvidia/cBench_V1.1/telecom_gsm/src_work/out.perf'

# 本地目录路径
local_dir = '/home/jiayu/cBench_V1.1/telecom_gsm/src_work/'

# 建立 SSH 连接
ssh_connection.get(remote_file_path, local=local_dir)
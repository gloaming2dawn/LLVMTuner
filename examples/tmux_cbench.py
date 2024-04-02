import subprocess
import time

# 定义要执行的 Python 程序和对应的 tmux 会话名称
python_programs = {
    '3': 'python all_run_cBench_ssh.py --device=3',
    '1': 'python all_run_cBench_ssh.py --device=1',
    '5': 'python all_run_cBench_ssh.py --device=5',
    '6': 'python all_run_cBench_ssh.py --device=6',
    '4': 'python all_run_cBench_ssh.py --device=4',
    # 添加更多的会话和对应的 Python 程序
}

# 遍历字典，为每个会话创建一个新的 tmux 会话并执行对应的 Python 程序
for session_name, program_name in python_programs.items():
    # # 创建新的 tmux 会话
    # subprocess.run(['tmux', 'new-session', '-d', '-s', session_name])
    # 在新的 tmux 会话中执行 Python 程序
    subprocess.run(['tmux', 'send-keys', '-t', session_name, program_name, 'Enter'])
    # 等待一段时间，确保 Python 程序有足够的时间启动
    time.sleep(0.5)

# # 程序执行完成后，等待用户按下任意键退出
# input("Press any key to exit...")

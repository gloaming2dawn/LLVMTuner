import os
import shutil
import hashlib

def copy_folder(src_dir, dst_dir):
    """
    复制一个文件夹及其所有内容到另一个目录。

    参数:
    - src_dir: 源文件夹的路径。
    - dst_dir: 目标文件夹的路径。
    """
    try:
        # 将src_dir复制到dst_dir，包括其所有内容
        shutil.copytree(src_dir, dst_dir)
        print(f"Folder '{src_dir}' was successfully copied to '{dst_dir}'.")
    except shutil.Error as e:
        # shutil.Error 异常将会列出由于哪些原因导致复制操作失败的文件。
        print(f"Error occurred while copying folder. Details: {e}")
    except FileExistsError:
        # 如果dst_dir已经存在，将会抛出此异常。
        print(f"The destination '{dst_dir}' already exists.")

def merge_directories(destination_dir, source_dirs):
    
    # 创建目标目录
    os.makedirs(destination_dir, exist_ok=True)
    
    # 遍历每个源目录
    for source_dir in source_dirs:
        assert os.path.exists(source_dir)
        # 遍历源目录中的文件和子目录
        for item in os.listdir(source_dir):
            source_item = os.path.join(source_dir, item)
            destination_item = os.path.join(destination_dir, item)
            # print(source_dir,source_item,destination_item)
            # assert 1==0
            
            # 如果是子目录，则递归调用 merge_directories
            if os.path.isdir(source_item):
                merge_directories(destination_item, [source_item])
            # 如果是文件，则直接复制到目标目录
            else:
                shutil.copy2(source_item, destination_item)

def remove_files_in_dir(dir_path):
    """
    删除指定目录下的所有直接文件，保留子目录及其内容不变。
    
    参数:
    - dir_path: 要清理的目录路径
    """
    # 检查目录是否存在
    if not os.path.exists(dir_path):
        print(f"The directory {dir_path} does not exist.")
        return
    
    # 遍历目录下的所有项
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)  # 获取项的完整路径
        # 如果是文件，则删除
        if os.path.isfile(item_path):
            os.remove(item_path)

def count_subdirectories(directory):
    # 获取当前目录下的所有子文件夹
    subdirectories = [name for name in os.listdir(directory) if os.path.isdir(os.path.join(directory, name))]
    
    # 遍历每个子文件夹
    for subdir in subdirectories:
        subdir_path = os.path.join(directory, subdir)
        # 统计当前子文件夹下的直接子文件夹数量
        subdir_count = len([name for name in os.listdir(subdir_path) if os.path.isdir(os.path.join(subdir_path, name))])
        # 输出结果
        print(f"Subdirectory: {subdir}, Subdirectories: {subdir_count}")

def check_and_clean_directory(base_dir):
    """
    检查并清理指定目录。

    参数:
    - base_dir: 输入的基础目录路径。
    """
    if not os.path.exists(base_dir):
        print(f"The directory {base_dir} does not exist.")
        return
    
    # 遍历基础目录下的所有直接子文件夹
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path):
            # 如果子文件夹名称为'LLVMTuner-cfg'，删除该文件夹
            if item == 'LLVMTuner-cfg':
                shutil.rmtree(item_path)
                print(f"Deleted folder: {item_path}")
            else:
                # 检查该文件夹下的直接子文件夹
                check_subdirectories(item_path)

def check_subdirectories(dir_path):
    """
    检查指定目录下的直接子文件夹，确保它们以'IR-'开头。

    参数:
    - dir_path: 要检查的目录路径。
    """
    all_md5sums=[]
    for subdir in os.listdir(dir_path):
        subpath = os.path.join(dir_path, subdir)
        if not os.path.isdir(subpath):
            raise ValueError(f"Item {subdir} in {dir_path} is not a directory")
        if not subdir.startswith('IR-'):
            raise ValueError(f"Directory {subdir} in {dir_path} does not start with 'IR-'")

        files = os.listdir(subpath)
        opt_bc_files = [f for f in files if f.endswith('.opt.bc')]
        if not opt_bc_files:
            print(f"No '.opt.bc' file found in {subpath}. Deleting...")
            shutil.rmtree(subpath)
            continue
        elif len(opt_bc_files) > 1:
                raise ValueError(f"Multiple '.opt.bc' files found in {subpath}")
        else:
            hashobj = hashlib.md5()
            with open(os.path.join(subpath, opt_bc_files[0]), 'rb') as f:
                hashobj.update(f.read())
            md5sum=hashobj.hexdigest()
            if md5sum in all_md5sums:
                # print(f"Duplicate file found in {subpath}. Deleting...")
                shutil.rmtree(subpath)
            else:
                all_md5sums.append(md5sum)
                
            


        

def calc_md5(file_path):
    """
    计算指定文件的MD5哈希值。
    
    参数:
    - file_path: 文件的完整路径。
    
    返回:
    - 该文件的MD5哈希值。
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def find_duplicate_opt_bc_files(dir_path):
    """
    在指定目录及其子目录下查找所有以'.opt.bc'结尾的文件，并检测是否有重复文件。
    
    参数:
    - dir_path: 要搜索的目录的路径。
    
    返回:
    - 无。直接打印找到的重复文件信息。
    """
    md5_to_file = {}  # 用于映射MD5值到文件路径
    duplicates = False  # 标记是否找到重复文件
    
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith('.opt.bc'):
                file_path = os.path.join(root, file)
                file_md5 = calc_md5(file_path)
                
                if file_md5 in md5_to_file:
                    # print(f"Duplicate file found: {file_path} is a duplicate of {md5_to_file[file_md5]}")
                    duplicates = True
                else:
                    md5_to_file[file_md5] = file_path
    
    if not duplicates:
        print("No duplicate '.opt.bc' files found.")
    else:
        print("Number after remove duplicate IRs", len(md5_to_file))


# 示例用法
if __name__ == "__main__":
    final_benchmarks =['automotive_bitcount', 'automotive_qsort1', 'bzip2d', 'bzip2e', 'consumer_jpeg_c', 'consumer_jpeg_d', 'consumer_lame', 'consumer_tiff2bw', 'consumer_tiff2rgba', 'consumer_tiffdither', 'security_blowfish_d', 'security_blowfish_e', 'security_sha', 'telecom_gsm']
    final_benchmarks = ['telecom_gsm']

    # final_benchmarks=['automotive_bitcount']
    # find_duplicate_opt_bc_files('/home/jiayu/result_llvmtuner_17/cBench/automotive_bitcount/one-for-all-random/bitcnt_2')
    # find_duplicate_opt_bc_files('/home/jiayu/result_llvmtuner_17/cBench/automotive_bitcount/nevergrad/bitcnt_2')
    # find_duplicate_opt_bc_files('/home/jiayu/result_llvmtuner_17/cBench/automotive_bitcount/nevergrad/bitcnt_3')

    for ben in final_benchmarks:
        destination_directory=f'/home/jiayu/result_llvmtuner_17/cBench/{ben}/used'
        source_directories = [
            f'/home/jiayu/result_llvmtuner_17/cBench/{ben}/random',
            f'/home/jiayu/result_llvmtuner_17/cBench/{ben}/one-for-all-random',
        ]

        merge_directories(destination_directory, source_directories)
        print(f"{ben}/BO merged successfully!")
        # count_subdirectories(destination_directory)
        remove_files_in_dir(destination_directory)
        check_and_clean_directory(destination_directory)
        count_subdirectories(destination_directory)
        copy_folder(destination_directory, f'/home/jiayu/result_llvmtuner_17/cBench/{ben}/local')
        






    # # 目标目录
    # destination_directory = "/home/jiayu/result_llvmtuner_17/cBench/telecom_gsm/BO"
    
    # # 源目录列表
    # source_directories = [
    #     "/home/jiayu/result_llvmtuner_17/cBench/telecom_gsm/random",
    #     "/home/jiayu/result_llvmtuner_17/cBench/telecom_gsm/one-for-all-random",
    #     # 添加更多的源目录...
    # ]
    
    # # 合并目录
    # merge_directories(destination_directory, source_directories)
    # print("Directories merged successfully!")

    # # 清除不必要的文件
    # remove_files_in_dir(destination_directory)

    # # 统计IR数量
    # count_subdirectories(destination_directory)

    # check_and_clean_directory(destination_directory)

    # count_subdirectories(destination_directory)



def collect_pmu():
    try:
        ret = ssh_connection.put(local=os.path.join(build_dir,'a.out'), remote=run_dir)
    except Exception as e:
        try:
            time.sleep(3)
            ret = ssh_connection.put(local=os.path.join(build_dir,'a.out'), remote=run_dir)
        except Exception as e:
            try:
                time.sleep(3)
                ret = ssh_connection.put(local=os.path.join(build_dir,'a.out'), remote=run_dir)
            except Exception as e:
                assert 1==0, [os.path.join(build_dir,'a.out'), run_dir]

    try:
        timeout_seconds = 20
        with ssh_connection.cd(run_dir):
            perf_cmd = 'perf stat -e branch-misses,cache-misses,cache-references,cpu-cycles,instructions,cpu-clock,L1-dcache-load-misses,L1-dcache-loads,L1-dcache-store-misses,L1-dcache-stores,branch-load-misses,branch-loads'
            ret=ssh_connection.run(f'timeout {timeout_seconds} {perf_cmd} {run_cmd}' , hide=True, timeout=timeout_seconds) 
            # some benchmarks have bug, we need to clear the output, otherwise the next run will cost much more time
            if args.benchmark == 'consumer_tiff2rgba':
                ssh_connection.run(f'rm output_largergba.tif' , hide=True, timeout=timeout_seconds)
            if args.benchmark == 'consumer_jpeg_d':
                ssh_connection.run(f'rm output_large_decode.ppm' , hide=True, timeout=timeout_seconds)
            if args.benchmark == 'consumer_tiffmedian':
                ssh_connection.run(f'rm output_largemedian.tif' , hide=True, timeout=timeout_seconds)
            if args.benchmark == 'security_rijndael_d':
                ssh_connection.run(f'rm output_large.dec' , hide=True, timeout=timeout_seconds)
            if args.benchmark == 'security_rijndael_e':
                ssh_connection.run(f'rm output_large.enc' , hide=True, timeout=timeout_seconds)

        temp=ret.stderr.strip()
        real=temp.split('\n')[-3]
        searchObj = re.search( r'real\s*(.*)m(.*)s.*', temp)
        runtime = int(searchObj[1])*60+float(searchObj[2])



    except invoke.exceptions.UnexpectedExit:
        runtime = inf
    except invoke.exceptions.CommandTimedOut:
        runtime = inf   

    lines = temp.strip().split('\n')
    features = {}
    for line in lines:
        match = re.search(r'(\d+(?:,\d+)*)\s+(\w+(?:-\w+)*)', line)
        if match:
            value = match.group(1).replace(',', '')
            key = match.group(2)
            features[key] = int(value)
    
    pmu_events = 'branch-misses,cache-misses,cache-references,cpu-cycles,instructions,cpu-clock,L1-dcache-load-misses,L1-dcache-loads,L1-dcache-store-misses,L1-dcache-stores,branch-load-misses,branch-loads'.split(',')
    pmu = {k: features[k] for k in pmu_events}     
    
    return pmu










    if args.method == 'O3':
        # f.hotfiles = allfiles
        fun.repeat = 10
        fun.adaptive_measure = False
        y = fun('default<O3>')
    
    if args.method == 'O3/O1':
        # f.hotfiles = allfiles
        fun.repeat = 5
        fun.adaptive_measure = False
        y_O1 = fun('default<O1>')
        y_O3 = fun('default<O3>')
        print('O3/O1 speedup',y_O1/y_O3)
    
    if args.method == 'perf':
        module2funcnames = fun_O3._get_func_names()
        fun_O3.repeat = 1
        fun_O3('default<O3>')
        folded_perf_result = perf_record(ssh_connection, build_dir, run_dir, run_cmd)
        hotfiles,hotfiles_details = gen_hotfiles(module2funcnames, binary_name, folded_perf_result)
        print(hotfiles, hotfiles_details)
        with open(f'{args.benchmark}_hotfiles.json','w') as file:
            json.dump(hotfiles_details, file, indent=4)
    
    if args.method == 'cost_model':
        pmu_savepath = os.path.join(tmp_dir, 'pmu_O3.txt')
        pmu_cmd = f'python collect_PMU.py --device={args.device} --benchmark={args.benchmark} --optlevel=O3 2> {pmu_savepath}'
        subprocess.run(pmu_cmd, shell=True)

        pmu_savepath = os.path.join(tmp_dir, 'pmu_O0.txt')
        pmu_cmd = f'python collect_PMU.py --device={args.device} --benchmark={args.benchmark} --optlevel=O0 2> {pmu_savepath}'
        subprocess.run(pmu_cmd, shell=True)

        # hotfiles=ben2hot[args.benchmark]
        # hotfiles = hotfiles[:1]
        # fun = Function_wrap(ccmd, build_dir, tmp_dir, run_and_eval_fun, hotfiles)
        # len_seq=120


        # params={}
        # filename = fun.hotfiles[0]
        # fileroot,fileext=os.path.splitext(filename)
        # for ii in range(args.budget):
        #     seq=random.choices(passes, k=len_seq)
        #     params[fileroot]=passlist2str(deepcopy(seq))
        #     y = fun(deepcopy(params))


    if args.method == 'collect_pmu':
        hotfiles=ben2hot[args.benchmark]
        hotfiles = hotfiles[:1]
        fun = Function_wrap(ccmd, build_dir, tmp_dir, run_and_eval_fun, hotfiles)
        data_path = f'/home/jiayu/result_llvmtuner_17/cBench/{args.benchmark}'
        with open(f'{data_path}/cost_model/result.json','r') as file:
            ic = 0
            for line in file:
                # 将每行的内容从JSON字符串转换为列表
                cfgpath, time = json.loads(line)
                with open(cfgpath, 'r') as file:
                    cfg=json.load(file)
                fun.build(cfg['params'])
                pmu = collect_pmu()
                cfg['pmu'] = pmu
                with open(cfgpath, 'w') as file:
                    json.dump(cfg, file, indent=4)
                ic = ic+1
                print(ic, cfgpath)
                

                


        






    
    if args.method == 'O3-random':
        def random_params():
            params={}
            for filename in fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                seq=random.choices(passes, k=len_seq)
                seq=check_seq(seq)
                params[fileroot]='-O3 ' + ' '.join(seq)
            return params
        
        params_list = []
        for _ in range(args.budget):
            params = random_params()
            params_list.append(params)
        
        t0 = time.time()
        with Pool(50) as p:
            flags = p.map(fun.gen_optIR, params_list)
        print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        
        for i in range(len(params_list)):
            if flags[i]:
                y = fun(params_list[i])
        
        print(f'{args.benchmark} {args.budget} iterations cost:',time.time()-t0)


    if args.method=='random':
        def random_params(i):
            params={}
            for fileroot in fun.hotfiles:
                # fileroot,fileext=os.path.splitext(filename)
                seq=random.choices(passes, k=len_seq)
                params[fileroot]=passlist2str(deepcopy(seq))
            return params
        
        params_list = []
        t0 = time.time()
        with Pool(50) as p:
            params_list = list(p.map(random_params, range(args.budget)))

        # for _ in range(args.budget):
        #     params = random_params()
        #     params_list.append(params)
        # print(f'time of generating params:',time.time()-t0)
        
        t0 = time.time()
        with Pool(50) as p:
            flags = p.map(fun.gen_optIR, params_list)
        # print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        # print(f"Number of successful compilation: {sum(flags)}")

        
        for i in range(len(params_list)):
            if flags[i]:
                y = fun(params_list[i])
        
        print(f'{args.benchmark} {args.budget} iterations cost:',time.time()-t0)
    
    if args.method=='random-all':
        def random_params(i):
            params={}
            for filename in fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                seq=random.choices(passes, k=len_seq)
                params[fileroot]=passlist2str(deepcopy(seq))
            return params
        
        params_list = []
        t0 = time.time()
        with Pool(50) as p:
            params_list = list(p.map(random_params, range(args.budget)))

        # for _ in range(args.budget):
        #     params = random_params()
        #     params_list.append(params)
        print(f'time of generating params:',time.time()-t0)
        
        t0 = time.time()
        with Pool(50) as p:
            flags = p.map(fun.gen_optIR, params_list)
        print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        print(f"Number of successful compilation: {sum(flags)}")

        
        for i in range(len(params_list)):
            if flags[i]:
                y = fun(params_list[i])
        
        print(f'{args.benchmark} {args.budget} iterations cost:',time.time()-t0)
    
    if args.method=='random-len100':
        len_seq = 100
        def random_params(i):
            params={}
            for filename in fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                seq=random.choices(passes, k=len_seq)
                params[fileroot]=passlist2str(deepcopy(seq))
            return params
        
        params_list = []
        t0 = time.time()
        with Pool(50) as p:
            params_list = list(p.map(random_params, range(args.budget)))

        # for _ in range(args.budget):
        #     params = random_params()
        #     params_list.append(params)
        print(f'time of generating params:',time.time()-t0)
        
        t0 = time.time()
        with Pool(50) as p:
            flags = p.map(fun.gen_optIR, params_list)
        print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        print(f"Number of successful compilation: {sum(flags)}")

        
        for i in range(len(params_list)):
            if flags[i]:
                y = fun(params_list[i])
        
        print(f'{args.benchmark} {args.budget} iterations cost:',time.time()-t0)
    
    if args.method=='random-len80':
        len_seq = 80
        def random_params(i):
            params={}
            for filename in fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                seq=random.choices(passes, k=len_seq)
                params[fileroot]=passlist2str(deepcopy(seq))
            return params
        
        params_list = []
        t0 = time.time()
        with Pool(50) as p:
            params_list = list(p.map(random_params, range(args.budget)))

        # for _ in range(args.budget):
        #     params = random_params()
        #     params_list.append(params)
        print(f'time of generating params:',time.time()-t0)
        
        t0 = time.time()
        with Pool(50) as p:
            flags = p.map(fun.gen_optIR, params_list)
        print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        print(f"Number of successful compilation: {sum(flags)}")

        
        for i in range(len(params_list)):
            if flags[i]:
                y = fun(params_list[i])
        
        print(f'{args.benchmark} {args.budget} iterations cost:',time.time()-t0)
        
            
            
    if args.method=='one-for-all-random': 
        def random_params_one(i):
            seq=random.choices(passes, k=len_seq)
            for filename in fun.hotfiles:
                fileroot,fileext=os.path.splitext(filename)
                params=passlist2str(deepcopy(seq))
            return params
        
        params_list=[]
        t0 = time.time()
        with Pool(50) as p:
            params_list = list(p.map(random_params_one, range(args.budget)))
        print(f'time of generating params:',time.time()-t0)
        # for _ in range(args.budget):
        #     params = random_params_one()
        #     params_list.append(params)
            # y = f(' '.join(seq))
        
        t0 = time.time()
        with Pool(50) as p:
            flags = p.map(fun.gen_optIR, params_list)
        print(f'time of parallel generating {args.budget} optimized IRs:',time.time()-t0)
        print(f"Number of successful compilation: {sum(flags)}")
        
        for i in range(len(params_list)):
            if flags[i]:
                y = fun(params_list[i])
        print(f'{args.benchmark} {args.budget} iterations cost:',time.time()-t0)



    
    if args.method=='test_best':
        methods = ['adaptive_local','nevergrad','random','one-by-one','one-for-all-random','one-for-all-nevergrad']
        # methods = ['random']
        y_O3 = fun('default<O3>')
        for method in methods:
            config_times = []
            # shortest_time = float('inf')
            with open(f'/home/jiayu/result_llvmtuner_17/data1-cBench/{args.benchmark}/{method}/result.json','r') as file:
                for line in file:
                    # 将每行的内容从JSON字符串转换为列表
                    config, time = json.loads(line)
                    config_times.append((config, time))
                    # # 检查运行时间是否为最短
                    # if time < shortest_time:
                    #     shortest_time = time
                    #     shortest_config = config
            sorted_config_times = sorted(config_times, key=lambda x: x[1])
            shortest_config, shortest_time = sorted_config_times[0]
            print(shortest_config, shortest_time)
            shortest_config = shortest_config.replace('cBench','data1-cBench')
            print(shortest_config)
            with open(shortest_config,'r') as file:
                data = json.load(file)
                params = data['params']
            
            fun.repeat = 10
            fun.adaptive_measure = False
            y = fun(params)
            print(method, y, y_O3/y)
            # print('speedup',y_O3/y)
        



    if args.method=='tab1':
        config_times = []
        # shortest_time = float('inf')
        with open('/home/jiayu/result_llvmtuner_17/cBench/telecom_gsm/one-for-all-random/result.json','r') as file:
            for line in file:
                # 将每行的内容从JSON字符串转换为列表
                config, time = json.loads(line)
                config_times.append((config, time))
                # # 检查运行时间是否为最短
                # if time < shortest_time:
                #     shortest_time = time
                #     shortest_config = config
        sorted_config_times = sorted(config_times, key=lambda x: x[1])
        shortest_config, shortest_time = sorted_config_times[0]
        print(shortest_config, shortest_time)
        with open(shortest_config,'r') as file:
            data = json.load(file)
            opt_str = data['params']


        str1 = 'default<O3>'
        str2 = opt_str

        # str1 = 'default<O3>'
        # str2 = 'default<O1>'

        params_O3={}
        for filename in fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            params_O3[fileroot] = 'default<O3>'
        fun.repeat = 10
        fun.adaptive_measure = False
        # y = fun(params_O3)


        params=deepcopy(params_O3)
        params['long_term'] = str1
        params['short_term'] = str1
        y = fun(params)
        print(f'long_term: str1, short_term:str1',y)

        # id = hashlib.md5(params['long_term'].encode('utf-8')).hexdigest()
        # obj1 = os.path.join(tmp_dir, 'long_term', f'IR-{id}','long_term.o')
        # id = hashlib.md5(params['short_term'].encode('utf-8')).hexdigest()
        # obj2 = os.path.join(tmp_dir, 'short_term', f'IR-{id}','short_term.o')
        # exe = os.path.join(build_dir, 'a.out')
        # tab1_dir = os.path.join(tmp_dir, 'LLVMTuner-cfg', f'{params["long_term"]}_{params["short_term"]}')
        # os.makedirs(tab1_dir, exist_ok=True)
        # subprocess.run(f'cp {obj1} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {obj2} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {exe} {tab1_dir}', shell=True)
        # objs_others = []
        # for filename in allfiles:
        #     fileroot,fileext=os.path.splitext(filename)
        #     obj = os.path.join(build_dir, f'{fileroot}.o')
        #     objs_others.append(obj)
        #     if fileroot in ['long_term']:
        #         subprocess.run(f'diff {obj1} {obj}', shell=True)
        
        # exe2 = os.path.join(tab1_dir, 'b.out')
        # # subprocess.run(f'clang {obj1} {obj2} {" ".join(objs_others)} {cross_flags} -o {exe2}', shell=True)
        # subprocess.run(f'clang {" ".join(objs_others)} {cross_flags} -lm -o {exe2}', shell=True)
        # subprocess.run(f'diff {exe} {exe2}', shell=True)

        

        params=deepcopy(params_O3)
        params['long_term'] = str2
        params['short_term'] = str1
        y = fun(params)
        print(f'long_term:str2, short_term:str1',y)

        # id = hashlib.md5(params['long_term'].encode('utf-8')).hexdigest()
        # obj1 = os.path.join(tmp_dir, 'long_term', f'IR-{id}','long_term.o')
        # id = hashlib.md5(params['short_term'].encode('utf-8')).hexdigest()
        # obj2 = os.path.join(tmp_dir, 'short_term', f'IR-{id}','short_term.o')
        # exe = os.path.join(build_dir, 'a.out')
        # tab1_dir = os.path.join(tmp_dir, 'LLVMTuner-cfg', f'{params["long_term"]}_{params["short_term"]}')
        # os.makedirs(tab1_dir, exist_ok=True)
        # subprocess.run(f'cp {obj1} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {obj2} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {exe} {tab1_dir}', shell=True)
        # objs_others = []
        # for filename in allfiles:
        #     fileroot,fileext=os.path.splitext(filename)
        #     obj = os.path.join(build_dir, f'{fileroot}.o')
        #     objs_others.append(obj)
        #     if fileroot in ['long_term']:
        #         subprocess.run(f'diff {obj1} {obj}', shell=True)
        
        # exe2 = os.path.join(tab1_dir, 'b.out')
        # # subprocess.run(f'clang {obj1} {obj2} {" ".join(objs_others)} {cross_flags} -o {exe2}', shell=True)
        # subprocess.run(f'clang {" ".join(objs_others)} {cross_flags} -lm -o {exe2}', shell=True)
        # subprocess.run(f'diff {exe} {exe2}', shell=True)


        params=deepcopy(params_O3)
        params['long_term'] = str1
        params['short_term'] = str2
        y = fun(params)
        print(f'long_term:str1, short_term:str2',y)

        # id = hashlib.md5(params['long_term'].encode('utf-8')).hexdigest()
        # obj1 = os.path.join(tmp_dir, 'long_term', f'IR-{id}','long_term.o')
        # id = hashlib.md5(params['short_term'].encode('utf-8')).hexdigest()
        # obj2 = os.path.join(tmp_dir, 'short_term', f'IR-{id}','short_term.o')
        # exe = os.path.join(build_dir, 'a.out')
        # tab1_dir = os.path.join(tmp_dir, 'LLVMTuner-cfg', f'{params["long_term"]}_{params["short_term"]}')
        # os.makedirs(tab1_dir, exist_ok=True)
        # subprocess.run(f'cp {obj1} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {obj2} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {exe} {tab1_dir}', shell=True)
        # objs_others = []
        # for filename in allfiles:
        #     fileroot,fileext=os.path.splitext(filename)
        #     obj = os.path.join(build_dir, f'{fileroot}.o')
        #     objs_others.append(obj)
        #     if fileroot in ['long_term']:
        #         subprocess.run(f'diff {obj1} {obj}', shell=True)
        
        # exe2 = os.path.join(tab1_dir, 'b.out')
        # # subprocess.run(f'clang {obj1} {obj2} {" ".join(objs_others)} {cross_flags} -o {exe2}', shell=True)
        # subprocess.run(f'clang {" ".join(objs_others)} {cross_flags} -lm -o {exe2}', shell=True)
        # subprocess.run(f'diff {exe} {exe2}', shell=True)


        params=deepcopy(params_O3)
        params['long_term'] = str2
        params['short_term'] = str2
        y = fun(params)
        print(f'long_term:str2, short_term:str2',y)

        # id = hashlib.md5(params['long_term'].encode('utf-8')).hexdigest()
        # obj1 = os.path.join(tmp_dir, 'long_term', f'IR-{id}','long_term.o')
        # id = hashlib.md5(params['short_term'].encode('utf-8')).hexdigest()
        # obj2 = os.path.join(tmp_dir, 'short_term', f'IR-{id}','short_term.o')
        # exe = os.path.join(build_dir, 'a.out')
        # tab1_dir = os.path.join(tmp_dir, 'LLVMTuner-cfg', f'{params["long_term"]}_{params["short_term"]}')
        # os.makedirs(tab1_dir, exist_ok=True)
        # subprocess.run(f'cp {obj1} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {obj2} {tab1_dir}', shell=True)
        # subprocess.run(f'cp {exe} {tab1_dir}', shell=True)
        # objs_others = []
        # for filename in allfiles:
        #     fileroot,fileext=os.path.splitext(filename)
        #     obj = os.path.join(build_dir, f'{fileroot}.o')
        #     objs_others.append(obj)
        #     if fileroot in ['long_term']:
        #         subprocess.run(f'diff {obj1} {obj}', shell=True)
        
        # exe2 = os.path.join(tab1_dir, 'b.out')
        # # subprocess.run(f'clang {obj1} {obj2} {" ".join(objs_others)} {cross_flags} -o {exe2}', shell=True)
        # subprocess.run(f'clang {" ".join(objs_others)} {cross_flags} -lm -o {exe2}', shell=True)
        # subprocess.run(f'diff {exe} {exe2}', shell=True)



    


    if args.method=='one-by-one':
        def allocate_budget(data, budget):
            # 计算总值
            total_value = sum(data.values())
            
            # 初始化结果字典
            result = {}
            
            # 根据值将预算分配给不同的键
            for key, value in data.items():
                result[key] = int(budget * (value / total_value))
            
            return result

        with open(f'{args.benchmark}_hotfiles.json', 'r') as file:
            data = json.load(file)
            d = {}
            for item in data:
                d[item[0]] = item[1]
            budgets = allocate_budget(d, args.budget)

        params={}
        for filename in fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            params[fileroot] = 'default<O3>'
        y = fun(params)

        for filename in fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            params=deepcopy(fun.best_params)
            for ii in range(budgets[fileroot]):
                seq=random.choices(passes, k=len_seq)
                params[fileroot]=passlist2str(deepcopy(seq))
                print(fileroot, ii, budgets[fileroot])
                y = fun(deepcopy(params))
            
            
                
        
                
        
    
    if args.method=='nevergrad':
        import nevergrad as ng
        import numpy as np
        len_seq = 100
        # optimizers = ng.optimizers.registry.keys()
        # print(list(optimizers))
        params_set = ng.p.Choice(
                choices=passes,
                repetitions=len_seq*len(fun.hotfiles),
                deterministic=True
            )
        
        optimizer=ng.optimizers.NGOpt(parametrization=params_set, budget=args.budget)
        # print(optimizer._select_optimizer_cls())

        def split_list(lst, num_chunks):
            avg = len(lst) // num_chunks
            return [lst[i:i+avg] for i in range(0, len(lst), avg)]

        count = 0
        previous_pass_list = ['*']*len_seq*len(fun.hotfiles)
        best_pass_list = ['*']*len_seq*len(fun.hotfiles)
        while count < args.budget:
            # if count <10:
            #     optimizer.suggest(random.choices(passes, k=len_seq*len(fun.hotfiles)))
            t0=time.time()
            x = optimizer.ask()
            print(f'ask time:',time.time()-t0)
            pass_list=list(x.value)
            n_changed = 0
            sum_changed = 0
            for i in range(len(pass_list)):
                if pass_list[i] != best_pass_list[i]:
                    n_changed += 1
                    sum_changed += i
            print(f'number of changed elements:',n_changed)
            print(f'sum of changed elements number:',sum_changed)
            previous_pass_list = pass_list

            seq_list = split_list(pass_list, len(fun.hotfiles))
            
            assert len(seq_list) == len(fun.hotfiles)
            params = {}
            for i in range(len(seq_list)):
                opt_str=passlist2str(seq_list[i])
                fileroot,fileext=os.path.splitext(fun.hotfiles[i])
                params[fileroot]=opt_str

            best_y = fun.best_y
            y=fun(params)
            if y != inf:
                t0=time.time()
                if y < best_y:
                    print(f'new best y:',y)
                    best_pass_list = pass_list
                optimizer.tell(x, y)
                print(f'tell time:',time.time()-t0)
                count += 1
                

    if args.method=='one-by-one-nevergrad':
        import nevergrad as ng
        import numpy as np
        # optimizers = ng.optimizers.registry.keys()
        # print(list(optimizers))
        params_set = ng.p.Choice(
                choices=passes,
                repetitions=len_seq,
                deterministic=True
            )
        
        params={}
        for filename in fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            params[fileroot] = 'default<O3>'
        y = fun(params)

        for filename in fun.hotfiles:
            fileroot,fileext=os.path.splitext(filename)
            params=deepcopy(fun.best_params)
            while count < args.budget:
                t0=time.time()
                x = optimizer.ask()
                print(f'ask time:',time.time()-t0)
                pass_list=list(x.value)
                params[fileroot]=passlist2str(deepcopy(pass_list))
                y = fun(deepcopy(params))
        
        optimizer=ng.optimizers.NGOpt(parametrization=params_set, budget=args.budget)
        # print(optimizer._select_optimizer_cls())

        

        count = 0
        previous_pass_list = ['*']*len_seq*len(fun.hotfiles)
        while count < args.budget:
            # if count <10:
            #     optimizer.suggest(random.choices(passes, k=len_seq*len(fun.hotfiles)))
            t0=time.time()
            x = optimizer.ask()
            print(f'ask time:',time.time()-t0)
            pass_list=list(x.value)
            n_changed = 0
            for i in range(len(pass_list)):
                if pass_list[i] != previous_pass_list[i]:
                    n_changed += 1
            print(f'number of changed elements:',n_changed)
            previous_pass_list = pass_list

            
                

            seq_list = split_list(pass_list, len(fun.hotfiles))
            
            assert len(seq_list) == len(fun.hotfiles)
            params = {}
            for i in range(len(seq_list)):
                opt_str=passlist2str(seq_list[i])
                fileroot,fileext=os.path.splitext(fun.hotfiles[i])
                params[fileroot]=opt_str
            
            y=fun(params)
            if y != inf:
                t0=time.time()
                optimizer.tell(x, y)
                print(f'tell time:',time.time()-t0)
                count += 1

    if args.method=='one-for-all-nevergrad':
        import nevergrad as ng
        import numpy as np
        # optimizers = ng.optimizers.registry.keys()
        # print(list(optimizers))
        params_set = ng.p.Choice(
                choices=passes,
                repetitions=len_seq,
                deterministic=True
            )
        
        optimizer=ng.optimizers.NGOpt(parametrization=params_set, budget=args.budget)
        # print(optimizer._select_optimizer_cls())

        count = 0
        while count < args.budget:
            # if count <10:
            #     optimizer.suggest(random.choices(passes, k=len_seq*len(fun.hotfiles)))
            t0=time.time()
            x = optimizer.ask()
            print(f'ask time:',time.time()-t0)
            pass_list=list(x.value)
            params = passlist2str(pass_list)            
            y=fun(params)
            if y != inf:
                t0=time.time()
                optimizer.tell(x, y)
                print(f'tell time:',time.time()-t0)
                count += 1

    if args.method=='local':
        optimizer=Localoptimizer(
            fun=fun,
            passes=passes, 
            precompiled_path=tmp_dir,
            len_seq=len_seq,
            budget=args.budget, 
            n_init=20,
            failtol=50,
            )

        optimizer.minimize()

    if args.method=='adaptive_local':
        optimizer=Adalocaloptimizer(
            fun=fun,
            passes=passes, 
            precompiled_path=tmp_dir,
            len_seq=len_seq,
            budget=args.budget, 
            n_init=2,
            failtol=50,
            )

        optimizer.minimize()

    if args.method=='BO':
        config_times = []
        # shortest_time = float('inf')
        method = 'adaptive_local'
        with open(f'/home/jiayu/result_llvmtuner_17/cBench/{args.benchmark}/{method}/result.json','r') as file:
            for line in file:
                # 将每行的内容从JSON字符串转换为列表
                config, time = json.loads(line)
                config_times.append((config, time))
        sorted_config_times = sorted(config_times, key=lambda x: x[1])
        shortest_config, shortest_time = sorted_config_times[0]
        with open(shortest_config,'r') as file:
            data = json.load(file)
            best_params = data['params']

        initial_guess = {}
        for fileroot in best_params:
            if fileroot == 'long_term':
                initial_guess[fileroot] = best_params[fileroot]
            else:
                initial_guess[fileroot] = 'default<O3>'

        # fun(initial_guess)

        initial_guess = {'long_term': best_params['long_term']}
        fun.hotfiles = ['long_term.c']
        fun(initial_guess)

        BO=BO(
            fun=fun,
            passes=passes, 
            precompiled_path=tmp_dir,
            len_seq=len_seq,
            budget=args.budget, 
            acqf='EI',
            beta=1.96,
            n_parallel=args.n_parallel,
            n_init=20,
            failtol=50,
            min_cuda=20,
            device=args.server,
            initial_guess = initial_guess,
            )

        BO.minimize()

    
        
        
    if args.method == 'reduce':
        methods = ['adaptive_local','nevergrad']
        methods = ['one-by-one']
        m2best={}
        for method in methods:
            config_times = []
            # shortest_time = float('inf')
            with open(f'/home/jiayu/result_llvmtuner_17/cBench/{args.benchmark}/{method}/result.json','r') as file:
                for line in file:
                    # 将每行的内容从JSON字符串转换为列表
                    config, time = json.loads(line)
                    config_times.append((config, time))
            sorted_config_times = sorted(config_times, key=lambda x: x[1])
            shortest_config, shortest_time = sorted_config_times[0]
            print(shortest_config, shortest_time)
            m2best[method] = [shortest_time,shortest_config]
            with open(shortest_config,'r') as file:
                data = json.load(file)
                params = data['params']
            params, y_ref = fun.reduce_pass(params)
            cfg_path = os.path.join(fun.cfg_dir, 'cfg-{}.json'.format( hashlib.md5(str(params).encode('utf-8')).hexdigest()) )
            dirname=os.path.expanduser('~/LLVM17_reduced_cBench_result')
            file=os.path.join(dirname,f'{args.benchmark}_reduce_best.json')
            data=[method, cfg_path, y_ref]
            with open(file, 'a') as ff:
                ff.write(json.dumps(data)+'\n')
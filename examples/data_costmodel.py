import json
import os
import numpy as np
import hashlib
import re
from multiprocessing import Pool



#通过gen_llvm_transform_stats_key.py自动获取的pass_stats_keys（特征），当前仅在LLVM17测试
features = {'dse':'NumRedundantStores NumFastStores NumFastOther NumCompletePartials NumModifiedStores',
            
            'licm':'NumCreatedBlocks NumClonedBranches NumSunk NumHoisted NumMovedLoads NumMovedCalls NumLoadPromoted NumLoadStorePromoted NumMinMaxHoisted NumGEPsHoisted NumAddSubHoisted',
            
            'loop-idiom':'NumMemSet NumMemCpy NumMemMove',
            
            'adce':'NumRemoved NumBranchesRemoved', 
            
            'loop-delete':'NumDeleted',
            
            'constraint-elimination':'NumCondsRemoved',
            
            'gvn':'NumGVNInstr NumGVNLoad NumGVNPRE NumGVNBlocks NumGVNSimpl NumGVNEqProp NumPRELoad NumPRELoopLoad NumPRELoadMoved2CEPred',
            
            'indvars':'NumWidened NumReplaced NumLFTR NumElimExt NumElimIV NumElimIdentity NumElimOperand NumFoldedUser NumElimRem NumSimplifiedSDiv NumSimplifiedSRem NumElimCmp',
            
            'early-cse':'NumSimplify NumCSE NumCSECVP NumCSELoad NumCSECall NumDSE',
            
            'correlated-value-propagation': 'NumPhis NumPhiCommon NumSelects NumMemAccess NumCmps NumReturns NumDeadCases NumSDivSRemsNarrowed NumSDivs NumUDivURemsNarrowed NumAShrsConverted NumAShrsRemoved NumSRems NumSExt NumSICmps NumAnd NumNW NumNSW NumNUW NumAddNW NumAddNSW NumAddNUW NumSubNW NumSubNSW NumSubNUW NumMulNW NumMulNSW NumMulNUW NumShlNW NumShlNSW NumShlNUW NumAbs NumOverflows NumSaturating NumNonNull NumMinMax NumUDivURemsNarrowedExpanded',
            
            'jump-threading': 'NumThreads NumFolds NumDupes',
            
            'reassociate': 'NumChanged NumAnnihil NumFactor',
            
            'loop-interchange': 'LoopsInterchanged',
            
            'simple-loop-unswitch': 'NumBranches NumSwitches NumSelects NumGuards NumTrivial NumInvariantConditionsInjected',
            
            'loop-simplifycfg': 'NumTerminatorsFolded NumLoopBlocksDeleted NumLoopExitsDeleted',
            
            'memcpyopt': 'NumMemCpyInstr NumMemSetInfer NumMoveToCpy NumCpyToSet NumCallSlot',
            
            'sccp': 'NumInstRemoved NumInstReplaced NumArgsElimed NumGlobalConst',
            
            'bdce': 'NumRemoved NumSimplified NumSExt2ZExt',
            
            'simplifycfg':'NumSimpl',
            
            'loop-instsimplify':'NumSimplified',
            
            'loop-load-elim':'NumLoopLoadEliminted',
            
            'sroa':'NumAllocaPartitions NumNewAllocas NumPromoted NumLoadsSpeculated NumLoadsPredicated NumStoresPredicated NumDeleted NumVectorized',
            
            'callsite-splitting':'NumCallSiteSplit',

            'div-rem-pairs': 'NumPairs',

            'sink': 'NumSunk',

            'loop-fusion': 'FuseCounter',

            'tailcallelim':'NumEliminated',

            'loop-rotate':'NumRotated',

            'loop-unroll':'NumUnrolled NumCompletelyUnrolled NumUnrolledNotLatch NumRuntimeUnrolled',

            'simplifycfg':'NumSimpl NumBitMaps NumLinearMaps NumLookupTables NumFoldValueComparisonIntoPredecessors NumFoldBranchToCommonDest NumHoistCommonInstrs NumSinkCommonInstrs NumInvokes NumInvokesMerged NumInvokeSetsFormed',

            'libcalls-shrinkwrap':'NumWrappedOneCond NumWrappedTwoCond',

            'mem2reg':'NumPromoted NumLocalPromoted NumSingleStore NumDeadAlloca NumPHIInsert',

            'break-crit-edges':'NumBroken',

            'loop-peel':'NumPeeled',

            'lcssa':'NumLCSSA',

            'local':'NumRemoved NumPHICSEs',

            'build-libcalls': 'NumReadNone NumInaccessibleMemOnly NumReadOnly NumWriteOnly NumArgMemOnly NumInaccessibleMemOrArgMemOnly NumNoUnwind NumNoCapture NumWriteOnlyArg NumReadOnlyArg NumNoAlias NumNoUndef NumReturnedArg NumWillReturn',
            
            'loop-simplify':'NumNested',

            'aggressive-instcombine':'NumExprsReduced NumInstrsReduced NumAnyOrAllBitsSet NumGuardedRotates NumGuardedFunnelShifts',

            'instcombine': 'NumDeadStore NumGlobalCopies NumSel NumWorklistIterations NumCombined  NumConstProp NumDeadInst  NumSunkInst  NumExpand NumFactor    NumReassoc   NumSimplified NumPHIsOfInsertValues NumPHIsOfExtractValues NumPHICSEs NumAggregateReconstructionsSimplified NegatorNumTreesNegated NegatorNumInstructionsCreatedTotal NegatorNumInstructionsNegatedSuccess',

            'globalopt': 'NumMarked NumUnnamed NumSRA NumSubstitute NumDeleted NumGlobUses   NumLocalized  NumShrunkToBool   NumFastCallFns    NumCtorsEvaluated NumNestRemoved    NumAliasesResolved NumAliasesRemoved NumCXXDtorsRemoved NumInternalFunc NumColdCC',

            'elim-avail-extern':'NumRemovals NumConversions NumVariables',

            'inline':'NumInlined NumDeleted',

            'function-attrs': 'NumMemoryAttr NumNoCapture NumReturned NumReadNoneArg NumReadOnlyArg NumWriteOnlyArg NumNoAlias NumNonNullReturn NumNoRecurse NumNoUnwind NumNoFree NumWillReturn NumNoSync NumThinLinkNoRecurse NumThinLinkNoUnwind',

            'argpromotion':'NumArgumentsPromoted NumArgumentsDead',

            'globaldce':'NumAliases NumFunctions NumIFuncs NumVariables NumVFuncs',

            'constmerge':'NumIdenticalMerged',

            'deadargelim':'NumArgumentsEliminated NumRetValsEliminated NumArgumentsReplacedWithPoison',

            'vector-combine':'NumVecLoad NumVecCmp NumVecBO NumVecCmpBO NumShufOfBitcast NumScalarBO NumScalarCmp',

            'loop-vectorize':'LoopsVectorized LoopsEpilogueVectorized',

            'SLP':'NumVectorInstructions'
            }

# 我们通过opt得到的特征的形式是SLP.NumVectorInstructions
pass_stats_keys = []
for key in features:
    fks = features[key].split()
    for fk in fks:
        pass_stats_keys.append(key+'.'+fk)
pass_stats_keys = sorted(pass_stats_keys)

# 如何通过保存的cfg_path获取特征和PMU
def read_optstats_from_cfgpath(cfg_path):
    new_stats={}
    with open(cfg_path, 'r') as file:
        cfg=json.load(file)
    
    pmu = cfg['pmu']
    for filename in cfg['hotfiles']:
        fileroot = fileroot,fileext=os.path.splitext(filename)
        if isinstance(cfg['params'], (str)):
            opt_str=cfg['params']
        else:
            opt_str=cfg['params'][fileroot]
        
        stats_file = os.path.join(cfg['tmp_dir'], fileroot, 'IR-{}'.format( hashlib.md5(opt_str.encode('utf-8')).hexdigest() ),  fileroot+'.opt_stats')
        
        with open(stats_file, 'r') as f:
            stats=json.load(f)
        for key, value in stats.items():
            if key in pass_stats_keys:
                new_stats[fileroot+'.'+ key] = value
    return new_stats,pmu

#并行读取所有cfg_path的特征和PMU
def read_optstats_from_cfgpathlist(cfg_path_list, n_parallel = None):
    if n_parallel is not None:
        with Pool(n_parallel) as p:
            stats_and_pmu_list = p.map(read_optstats_from_cfgpath, cfg_path_list)
    else:
        with Pool() as p:
            stats_and_pmu_list = p.map(read_optstats_from_cfgpath, cfg_path_list)
    return stats_and_pmu_list

def read_pmu_from_file(file_path):
    with open(file_path, 'r') as file:
        temp = file.read()

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

#并行读取所有cfg_path的特征和PMU
def prepare_all(benchmark):
    data_path = f'/home/jiayu/result_llvmtuner_17/cBench/{benchmark}'
    with open(f'{data_path}/O3/result.json','r') as file:
        ys = []
        for line in file:
            # 将每行的内容从JSON字符串转换为列表
            config, time = json.loads(line)
            ys.append(time)
    y_O3 = np.mean(ys) #O3的运行时间
    cfgpath_list = []
    time_list = []
    speedup_list = []
    with open(f'{data_path}/cost_model/result.json','r') as file:
        for line in file:
            # 将每行的内容从JSON字符串转换为列表
            cfgpath, time = json.loads(line) #每个编译配置的路径和运行时间
            cfgpath_list.append(cfgpath)
            time_list.append(time)
            speedup_list.append(y_O3/time)

    stats_and_pmu_list = read_optstats_from_cfgpathlist(cfgpath_list)
    pmu_O0 = read_pmu_from_file(f'{data_path}/cost_model/pmu_O0.txt')
    pmu_O3 = read_pmu_from_file(f'{data_path}/cost_model/pmu_O3.txt')
    return stats_and_pmu_list, speedup_list, time_list, y_O3, pmu_O0, pmu_O3


if __name__ == "__main__":
    all_benchmarks = ['automotive_bitcount', 'automotive_qsort1', 'automotive_susan_c', 'automotive_susan_e', 'automotive_susan_s', 'bzip2d', 'bzip2e', 'consumer_jpeg_c', 'consumer_jpeg_d', 'consumer_lame', 'consumer_tiff2bw', 'consumer_tiff2rgba', 'consumer_tiffdither', 'consumer_tiffmedian', 'network_dijkstra', 'network_patricia', 'office_stringsearch1', 'security_blowfish_d', 'security_blowfish_e', 'security_rijndael_d', 'security_rijndael_e', 'security_sha', 'telecom_CRC32', 'telecom_adpcm_c', 'telecom_adpcm_d', 'telecom_gsm']
    # we donot use network_dijkstra because it is too noisy
    all_benchmarks.remove('network_dijkstra')

    for benchmark in all_benchmarks:
        data_path = f'/home/jiayu/result_llvmtuner_17/cBench/{benchmark}'
        stats_and_pmu_list, speedup_list, time_list, y_O3, pmu_O0, pmu_O3 = prepare_all(benchmark)
        print('='*10, benchmark,'='*10)
        # O0和O3的PMU
        print('PMU under -O0:', pmu_O0)
        print('PMU under -O3:', pmu_O3)

        # 这里只展示每个benchmark的第一个样本的特征和PMU
        # 特征的表示示例为bitcnts.break-crit-edges.NumBroken，其中bitcnts为文件名（我们只考虑了调优一个源文件，因此可以把文件名去掉），break-crit-edges.NumBroken为特征名，如果某个特征不包含在features中，则代表该feature为0
        print('features:', stats_and_pmu_list[0][0])
        print('PMU:', stats_and_pmu_list[0][1])
        print('speedup over -O3:', speedup_list[0])
        

        



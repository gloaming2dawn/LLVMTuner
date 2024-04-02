# -*- coding: utf-8 -*-
"""
Created on Tue Nov 15 08:37:06 2022

@author: jiayu
"""
import numpy as np
import hashlib
import subprocess
import os
import json
from multiprocessing import Pool
import llvmtuner
from llvmtuner.dict2vec import DictVectorizer
# from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import MinMaxScaler

possible_rbun=['early-cse.NumSimplify', 'gvn.NumGVNEqProp', 'gvn.NumGVNInstr', 'gvn.NumGVNLoad', 'gvn.NumGVNPRE', 'gvn.NumGVNSimpl', 'gvn.NumPRELoad', 'licm.NumPromoted', 'licm.NumSunk', 'loop-fusion.InvalidExitBlock', 'loop-fusion.InvalidExitingBlock', 'loop-fusion.MayThrowException', 'loop-fusion.UnknownTripCount', 'loop-unswitch.TotalInsts', 'reassociate.NumChanged', 'sccp.IPNumInstRemoved', 'sccp.NumDeadBlocks', 'sccp.NumInstRemoved', 'sink.NumSinkIter', 'sroa.NumAllocaPartitionUses', 'sroa.NumAllocaPartitions', 'sroa.NumDeleted']


#通过gen_llvm_transform_stats_key.py自动获取的pass_stats_keys，当前仅在LLVM10测试
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

pass_stats_keys = []
for key in features:
    fks = features[key].split()
    for fk in fks:
        pass_stats_keys.append(key+'.'+fk)
pass_stats_keys = sorted(pass_stats_keys)


# def read_optstats(stats_file):
#     with open(stats_file, 'r') as f:
#         data=f.read().splitlines()
#     start=data.index('{')
#     end=data.index('}')
#     data=data[start:end+1]
#     stats=json.loads(''.join(data))
#     # new_stats={key: value for key, value in stats.items() if '-' + key.split('.')[0] in passes}
#     new_stats={}
#     active_passes=set()
#     for key, value in stats.items():
#         p='-' + key.split('.')[0]
#         if p in passes:
#             new_stats[key]=value
#             active_passes.add(p)
#     return new_stats, active_passes

# def read_optstats(stats_file):
#     size = os.path.getsize(stats_file)
#     if size == 0:
#         return {}
#     else:
#         with open(stats_file, 'r') as f:
#             stats=json.load(f)
#             # try:
#             #     stats=json.load(f)
#             # except json.decoder.JSONDecodeError:
#             #     print(stats_file)
#             #     return {}
            
            
#     # new_stats={key: value for key, value in stats.items() if '-' + key.split('.')[0] in passes}
#     new_stats={}
#     active_passes=set()
#     bpasses=set()
#     for key, value in stats.items():
#         # p='-' + key.split('.')[0]
#         # bpasses.add(p)
#         if key in pass_stats_keys:
#             new_stats[key]=value
#             # active_passes.add(p)
#     return new_stats

# def read_optstats_from_dir(directory):
#     new_stats = {}
#     f_list = os.listdir(directory)
#     for f in f_list:
#         fileroot,fileext = os.path.splitext(f)
#         if fileext == '.opt_stats':
#             stats = read_optstats(os.path.join(directory,f))
#             stats={fileroot+'.'+ key: value for key, value in stats.items()}
#             new_stats.update(stats)
    
#     # with open(os.path.join(directory, 'opt_stats.json'),'w') as f:
#     #     json.dump(new_stats, f)
#     return new_stats

# def feature_extraction(dirs, passes):
#     with Pool(50) as p:
#         stats_list = p.map(read_optstats_from_dir, dirs)
#     v=DictVectorizer()
#     vector = v.fit_transform(stats_list).toarray()
#     feature_names = v.get_feature_names_out()
#     maxv=vector.max(axis=0)
#     maxv[maxv==0]=1
#     vector=vector/maxv
#     # Scaler = MinMaxScaler()
#     # vector = Scaler.fit_transform(vector)
#     return vector



      
# class read_optstats_from_cfgjson:
#     def __init__(self, tmp_dir):
#         self.tmp_dir = tmp_dir
        
#     def __call__(self, cfg_json):
#         new_stats={}
#         with open(cfg_json, 'r') as file:
#             cfg=json.load(cfg_json)
#             for fileroot, opt_str in cfg['params'].items():
#                 stats_file = os.path.join(cfg['tmp_dir'], fileroot, 'IR-{}'.format( hashlib.md5(opt_str.encode('utf-8')).hexdigest() ),  fileroot+'.opt_stats')
#                 with open(stats_file, 'r') as f:
#                     stats=json.load(f)
#                 for key, value in stats.items():
#                     if key in pass_stats_keys:
#                         new_stats[fileroot+'.'+ key] = value
#         return new_stats

def read_optstats_from_cfgpath(cfg_path):
    new_stats={}
    with open(cfg_path, 'r') as file:
        cfg=json.load(file)
    
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

    return new_stats


def read_optstats_from_cfgpathlist(cfg_path_list, n_parallel = None):
    if n_parallel is not None:
        with Pool(n_parallel) as p:
            stats_list = p.map(read_optstats_from_cfgpath, cfg_path_list)
    else:
        with Pool() as p:
            stats_list = p.map(read_optstats_from_cfgpath, cfg_path_list)
    return stats_list


        
def read_optstats_from_cfgjson(cfg_json):
    cfg = json.loads(cfg_json)
    new_stats={}
    for fileroot, opt_str in cfg['params'].items():
        stats_file = os.path.join(cfg['tmp_dir'], fileroot, 'IR-{}'.format( hashlib.md5(opt_str.encode('utf-8')).hexdigest() ),  fileroot+'.opt_stats')

        # with open(stats_file, 'r') as f:
        #     stats=json.load(f)
        # for key, value in stats.items():
        #     if key in pass_stats_keys:
        #         new_stats[fileroot+'.'+ key] = value

        if os.path.exists(stats_file):
            with open(stats_file, 'r') as f:
                stats=json.load(f)
            for key, value in stats.items():
                if key in pass_stats_keys:
                    new_stats[fileroot+'.'+ key] = value

        else:
            new_stats = None
    return new_stats


def read_optstats_from_cfgjsonlist(cfg_json_list, n_parallel = None):
    if n_parallel is not None:
        with Pool(n_parallel) as p:
            stats_list = p.map(read_optstats_from_cfgjson, cfg_json_list)
    else:
        with Pool() as p:
            stats_list = p.map(read_optstats_from_cfgjson, cfg_json_list)
    return stats_list



def stats2vec(stats_list):
    v=DictVectorizer(sparse=False)
    v.fit(stats_list)
    vector = np.array(v.transform(stats_list))
    maxv=vector.max(axis=0)
    maxv[maxv==0]=1
    vector=vector/maxv
    vector_initial = vector
    
    weights = np.zeros_like(maxv)
    feature_names = v.get_feature_names_out()
    # coarse_names = ['.'.join(x.split('.')[:-1]) for x in feature_names]
    # for name in np.unique(coarse_names):
    #     mask = (coarse_names==np.array(name))
    #     w = np.sqrt(1/mask.sum())
    #     weights[mask] = w
    # assert not np.any(weights == 0)
    # vector = vector*weights

    # Scaler = MinMaxScaler()
    # vector = Scaler.fit_transform(vector)
    return vector_initial, feature_names







# class test_read_optstats_from_dir:
#     def __init__(self, passes):
#         self.passes = passes
        
#     def __call__(self, directory):
#         all_active_passes = set()
#         all_stats = {}
#         f_list = os.listdir(directory)
#         for f in f_list:
#             fileroot,fileext = os.path.splitext(f)
#             if fileext == '.opt_stats':
#                 stats= read_optstats(os.path.join(directory, f), self.passes)
#                 all_active_passes=all_active_passes.union(bpasses)
#                 all_stats.update(stats)
        
#         return all_active_passes, all_stats
    
    
# def test_feature_extraction(dirs, passes):
#     with Pool(50) as p:
#         stats_list = p.map(read_optstats_from_dir, dirs)
#     # all_active_passes_list =[i for i, j in pass_stats_list]
#     # all_stats_list  = [j for i, j in pass_stats_list]
#     # all_active_passes = set().union(*all_active_passes_list)
#     all_stats=[]
#     for stats in stats_list:
#         all_stats.append(stats)
#     return all_stats

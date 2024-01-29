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
pass_stats_keys = ['SLP.NumVectorInstructions', #
                   'adce.NumBranchesRemoved', 'adce.NumRemoved', 
                   'alignment-from-assumptions.NumLoadAlignChanged', 'alignment-from-assumptions.NumMemIntAlignChanged', 'alignment-from-assumptions.NumStoreAlignChanged',
                   'argpromotion.NumAggregatesPromoted', 'argpromotion.NumArgumentsDead', 'argpromotion.NumArgumentsPromoted', 'argpromotion.NumByValArgsPromoted',
                   'attributor.NumAttributesFixedDueToRequiredDependences', 'attributor.NumAttributesManifested', 'attributor.NumAttributesTimedOut', 'attributor.NumAttributesValidFixpoint', 'attributor.NumFnWithExactDefinition', 'attributor.NumFnWithoutExactDefinition',
                   'bdce.NumRemoved', 'bdce.NumSimplified', 
                   'block-extractor.NumExtracted',
                   'break-crit-edges.NumBroken',
                   'build-libcalls.NumArgMemOnly', 'build-libcalls.NumNoAlias', 'build-libcalls.NumNoCapture', 'build-libcalls.NumNoUnwind', 'build-libcalls.NumNonNull', 'build-libcalls.NumReadNone', 'build-libcalls.NumReadOnly', 'build-libcalls.NumReadOnlyArg', 'build-libcalls.NumReturnedArg',
                   'callsite-splitting.NumCallSiteSplit',
                   'consthoist.NumConstantsHoisted', 
                   'constmerge.NumIdenticalMerged',
                   'constprop.NumInstKilled',
                   'correlated-value-propagation.NumAShrs', 'correlated-value-propagation.NumAddNSW', 'correlated-value-propagation.NumAddNUW', 'correlated-value-propagation.NumAddNW', 'correlated-value-propagation.NumAnd', 'correlated-value-propagation.NumCmps', 'correlated-value-propagation.NumDeadCases', 'correlated-value-propagation.NumMemAccess', 'correlated-value-propagation.NumMulNSW', 'correlated-value-propagation.NumMulNUW', 'correlated-value-propagation.NumMulNW', 'correlated-value-propagation.NumNSW', 'correlated-value-propagation.NumNUW', 'correlated-value-propagation.NumNW', 'correlated-value-propagation.NumOverflows', 'correlated-value-propagation.NumPhiCommon', 'correlated-value-propagation.NumPhis', 'correlated-value-propagation.NumReturns', 'correlated-value-propagation.NumSDivs', 'correlated-value-propagation.NumSExt', 'correlated-value-propagation.NumSRems', 'correlated-value-propagation.NumSaturating', 'correlated-value-propagation.NumSelects', 'correlated-value-propagation.NumShlNSW', 'correlated-value-propagation.NumShlNUW', 'correlated-value-propagation.NumShlNW', 'correlated-value-propagation.NumSubNSW', 'correlated-value-propagation.NumSubNUW', 'correlated-value-propagation.NumSubNW', 'correlated-value-propagation.NumUDivs',
                   'dce.DCEEliminated', 'dce.DIEEliminated', 
                   'deadargelim.NumArgumentsEliminated', 'deadargelim.NumArgumentsReplacedWithUndef', 'deadargelim.NumRetValsEliminated', 
                   'div-rem-pairs.NumDecomposed', 'div-rem-pairs.NumHoisted', 'div-rem-pairs.NumRecomposed', 
                   'dse.NumFastOther', 'dse.NumFastStores', 'dse.NumModifiedStores', 'dse.NumRedundantStores', 
                   'early-cse.NumCSE', 'early-cse.NumSimplify', 
                   'elim-avail-extern.NumFunctions', 'elim-avail-extern.NumVariables', 
                   'functionattrs.NumNoAlias', 'functionattrs.NumNoCapture', 'functionattrs.NumNoFree', 'functionattrs.NumNoRecurse', 'functionattrs.NumNoUnwind', 'functionattrs.NumNonNullReturn', 'functionattrs.NumReadNone', 'functionattrs.NumReadNoneArg', 'functionattrs.NumReadOnly', 'functionattrs.NumReadOnlyArg', 'functionattrs.NumReturned', 'functionattrs.NumWriteOnly', 
                   'globaldce.NumAliases', 'globaldce.NumFunctions', 'globaldce.NumIFuncs', 'globaldce.NumVFuncs', 'globaldce.NumVariables', 
                   'globalopt.NumAliasesRemoved', 'globalopt.NumAliasesResolved', 'globalopt.NumCXXDtorsRemoved', 'globalopt.NumColdCC', 'globalopt.NumDeleted', 'globalopt.NumFastCallFns', 'globalopt.NumGlobUses', 'globalopt.NumHeapSRA', 'globalopt.NumLocalized', 'globalopt.NumMarked', 'globalopt.NumNestRemoved', 'globalopt.NumSRA', 'globalopt.NumShrunkToBool', 'globalopt.NumSubstitute', 'globalopt.NumUnnamed', 
                   'gvn-hoist.NumCallsHoisted', 'gvn-hoist.NumCallsRemoved', 'gvn-hoist.NumHoisted', 'gvn-hoist.NumLoadsHoisted', 'gvn-hoist.NumLoadsRemoved', 'gvn-hoist.NumRemoved', 'gvn-hoist.NumStoresHoisted', 'gvn-hoist.NumStoresRemoved', 
                   'gvn-sink.NumRemoved', 
                   'gvn.NumGVNBlocks', 'gvn.NumGVNEqProp', 'gvn.NumGVNInstr', 'gvn.NumGVNLoad', 'gvn.NumGVNPRE', 'gvn.NumGVNSimpl', 'gvn.NumPRELoad',
                   'hotcoldsplit.NumColdRegionsOutlined', 
                   'indvars.NumElimCmp', 'indvars.NumElimExt', 'indvars.NumElimIV', 'indvars.NumElimIdentity', 'indvars.NumElimOperand', 'indvars.NumElimRem', 'indvars.NumFoldedUser', 'indvars.NumLFTR', 'indvars.NumReplaced', 'indvars.NumSimplifiedSDiv', 'indvars.NumSimplifiedSRem', 'indvars.NumWidened', 
                   'inline.NumCallsDeleted', 'inline.NumDeleted', 'inline.NumInlined', 'inline.NumMergedAllocas', 
                   'instcombine.NumCombined', 'instcombine.NumConstProp', 'instcombine.NumDeadInst', 'instcombine.NumDeadStore', 'instcombine.NumExpand', 'instcombine.NumFactor', 'instcombine.NumGlobalCopies', 'instcombine.NumReassoc', 'instcombine.NumSel', 'instcombine.NumSimplified', 'instcombine.NumSunkInst', 
                   'instsimplify.NumSimplified', 
                   'internalize.NumAliases', 'internalize.NumFunctions', 'internalize.NumGlobals', 
                   'ipconstprop.NumArgumentsProped', 'ipconstprop.NumReturnValProped', 
                   'jump-threading.NumDupes', 'jump-threading.NumFolds', 'jump-threading.NumThreads', 
                   'lcssa.NumLCSSA', 
                   'libcalls-shrinkwrap.NumWrappedOneCond', 'libcalls-shrinkwrap.NumWrappedTwoCond', 
                   'licm.NumClonedBranches', 'licm.NumCreatedBlocks', 'licm.NumHoisted', 'licm.NumMovedCalls', 'licm.NumMovedLoads', 'licm.NumPromoted', 'licm.NumSunk', 
                   'load-store-vectorizer.NumScalarsVectorized', 'load-store-vectorizer.NumVectorInstructions', 
                   'local.NumRemoved', 
                   'loop-data-prefetch.NumPrefetches', 
                   'loop-delete.NumDeleted', 
                   'loop-distribute.NumLoopsDistributed', 
                   'loop-extract.NumExtracted', 
                   'loop-fusion.FuseCounter',
                   'loop-idiom.NumMemSet', 
                   'loop-instsimplify.NumSimplified', 
                   'loop-interchange.LoopsInterchanged', 
                   'loop-load-elim.NumLoopLoadEliminted', 
                   'loop-predication.TotalWidened', 
                   'loop-rotate.NumRotated', 
                   'loop-simplify.NumNested', 
                   'loop-simplifycfg.NumLoopBlocksDeleted', 'loop-simplifycfg.NumLoopExitsDeleted', 'loop-simplifycfg.NumTerminatorsFolded', 
                   'loop-unroll-and-jam.NumCompletelyUnrolledAndJammed', 'loop-unroll-and-jam.NumUnrolledAndJammed', 
                   'loop-unroll.NumCompletelyUnrolled', 'loop-unroll.NumPeeled', 'loop-unroll.NumRuntimeUnrolled', 'loop-unroll.NumUnrolled', 'loop-unroll.NumUnrolledWithHeader', 
                   'loop-unswitch.NumBranches', 'loop-unswitch.NumGuards', 'loop-unswitch.NumSelects', 'loop-unswitch.NumSimplify', 'loop-unswitch.NumSwitches', 'loop-unswitch.NumTrivial', 
                   'loop-vectorize.LoopsVectorized', 
                   'loopsink.NumLoopSunk', 'loopsink.NumLoopSunkCloned', 
                   'lower-expect-intrinsic.ExpectIntrinsicsHandled',
                   'lower-is-constant-intrinsic.IsConstantIntrinsicsHandled', 'lower-is-constant-intrinsic.ObjectSizeIntrinsicsHandled', 
                   'lowerinvoke.NumInvokes', 
                   'mem2reg.NumPromoted', 'mem2reg.NumDeadAlloca', 'mem2reg.NumLocalPromoted', 'mem2reg.NumPHIInsert', 'mem2reg.NumSingleStore',
                   'memcpyopt.NumCpyToSet', 'memcpyopt.NumMemCpyInstr', 'memcpyopt.NumMemSetInfer', 'memcpyopt.NumMoveToCpy', 
                   'mergefunc.NumAliasesWritten', 'mergefunc.NumDoubleWeak', 'mergefunc.NumFunctionsMerged', 'mergefunc.NumThunksWritten',
                   'partial-inlining.NumColdOutlinePartialInlined', 'partial-inlining.NumColdRegionsOutlined', 'partial-inlining.NumPartialInlined',
                   'prune-eh.NumRemoved', 'prune-eh.NumUnreach', 
                   'reassociate.NumChanged', 'reassociate.NumAnnihil', 'reassociate.NumFactor', 
                   'sample-profile.NumCSInlined', 'sample-profile.NumCSNotInlined', 
                   'sccp.IPNumArgsElimed', 'sccp.IPNumInstRemoved', 'sccp.NumInstRemoved', 'sccp.IPNumGlobalConst'
                   'simple-loop-unswitch.NumBranches', 'simple-loop-unswitch.NumSwitches', 
                   'simplifycfg.NumBitMaps', 'simplifycfg.NumLinearMaps', 'simplifycfg.NumLookupTables', 'simplifycfg.NumSimpl', 'simplifycfg.NumSinkCommons', 'simplifycfg.NumSpeculations', 
                   'sink.NumSunk',
                   'spec-phis.NumEdgesSplit', 'spec-phis.NumNewRedundantInstructions', 'spec-phis.NumPHIsSpeculated', 'spec-phis.NumSpeculatedInstructions',
                   'sroa.NumAllocaPartitionUses', 'sroa.NumAllocaPartitions', 'sroa.NumDeleted', 'sroa.NumLoadsSpeculated', 'sroa.NumNewAllocas', 'sroa.NumPromoted', 'sroa.NumVectorized', 
                   'strip-dead-prototypes.NumDeadPrototypes', 
                   'tailcallelim.NumAccumAdded', 'tailcallelim.NumEliminated']



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
    
    weights = np.zeros_like(maxv)
    feature_names = v.get_feature_names_out()
    coarse_names = ['.'.join(x.split('.')[:-1]) for x in feature_names]
    for name in np.unique(coarse_names):
        mask = (coarse_names==np.array(name))
        w = np.sqrt(1/mask.sum())
        weights[mask] = w
    assert not np.any(weights == 0)
    vector_initial = vector
    vector = vector*weights
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

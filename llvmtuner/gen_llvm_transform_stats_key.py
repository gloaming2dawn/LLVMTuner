# -*- coding: utf-8 -*-

#python ../llvmtuner/gen_llvm_transform_stats_key.py --llvm-srcdir=/home/jiayu/llvm-project/
import os, argparse, re, json, sys
from multiprocessing import Pool
import llvmtuner
from llvmtuner.searchspace import default_space
from llvmtuner.feature_extraction import read_optstats_from_cfgpathlist

parser = argparse.ArgumentParser()
parser.add_argument('--llvm-srcdir', required=True, help='LLVM source code directory')
args = parser.parse_args()

passes, passes_clear, pass2kind, O3_trans_seq=default_space()
print(passes_clear)

llvm_debug_types = set()
llvm_transform_stats_keys = set()
llvm_dir = os.path.join(args.llvm_srcdir, "./llvm/lib/Transforms")
subdirs = os.listdir(llvm_dir)
subdirs.remove('Instrumentation')
for subdir in subdirs:
    directory = os.path.join(llvm_dir, subdir)
    if os.path.isdir(directory):
        f_list = os.listdir(directory)
        for f in f_list:
            fileroot,fileext = os.path.splitext(f)
            if fileext == '.cpp' and f != 'EntryExitInstrumentater.cpp':#366个
                # print(os.path.join(directory, f))
                with open(os.path.join(directory, f), 'r') as file:
                    data = file.read()
                info = re.findall('#define\s*DEBUG_TYPE\s*(.*?)\n', data, re.DOTALL)
                # info = re.findall(r'#define DEBUG_TYPE "(.*?)"', data, re.DOTALL)
                # assert len(info)<=1, {os.path.join(directory, f):info}
                types=[]
                for x in info:
                    if x.startswith('"'):
                        x=x.replace('"','')
                    else:
                        x_list = re.findall(f'#define\s*{x}\s*"(.*?)"', data, re.DOTALL)
                        assert len(x_list) ==1, os.path.join(directory, f)
                        x =x_list[0]
                    llvm_debug_types.add(x)
                    types.append(x)
                # if len(info)>1:
                #     print({os.path.join(directory, f):info})
                # if len(info)==1:
                #     llvm_debug_types.add(info[0])
                aa = re.findall('STATISTIC\s*\((.*?),\s*(.*?)\);\n', data, re.DOTALL)
                # aa = re.findall('STATISTIC\s*\((.*)\);\n', data)#\s*"(A-Za-z\s0-9]*?)"\)
                # for xx in aa:
                #     print(types[0], xx)

                
                stat = re.findall('STATISTIC\s*\(\s*([A-Za-z]*?)\s*,', data, re.DOTALL)
                if len(stat)>0:
                    assert len(types) == 1, os.path.join(directory, f)
                    for x in stat:
                        feature_key = types[0]+'.'+x
                        llvm_transform_stats_keys.add(feature_key)
                        # print(feature_key)
                
                        
                    
                
# print(llvm_debug_types)
# print(sorted(llvm_transform_stats_keys))
# print(len(llvm_transform_stats_keys))

transform_keys=set()
for key in llvm_transform_stats_keys:
    if 'Analyze' in key or 'analyze' in key:
        print(key)
    else:
        transform_keys.add(key)

transform_keys = sorted(list(transform_keys))
print(len(transform_keys))

# alltypes = [t for t in llvm_debug_types]
pass2type = {'loop-deletion':'loop-delete','loop-sink':'loopsink','correlated-propagation':'correlated-value-propagation','ipsccp':'sccp', 'lower-constant-intrinsics':'lower-is-constant-intrinsic','lower-expect':'lower-expect-intrinsic','slp-vectorizer':'SLP'}
for p in passes_clear:
    if p not in llvm_debug_types:
        if p in pass2type:
            if pass2type[p] in llvm_debug_types:
                continue
        else:
            print(p)

print('==='*20)
for t in llvm_debug_types:
    if t not in passes_clear and t not in pass2type.values():
        print(t)

print('==='*20)
def read_file(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return list(data.keys())

def get_opt_stats_files(directory):
    opt_stats_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.opt_stats'):
                file_path = os.path.join(root, file)
                if os.path.getsize(file_path) > 0:
                    opt_stats_files.append(os.path.join(root, file))
    return opt_stats_files

def merge_keys(directory):
    opt_stats_files = get_opt_stats_files(directory)
    
    with Pool() as pool:
        key_lists = pool.map(read_file, opt_stats_files)
    
    merged_keys = set()
    for key_list in key_lists:
        merged_keys.update(key_list)
    return list(merged_keys)


def get_unique_keys(directory):
    keys = set()

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".opt_stats"):
                file_path = os.path.join(root, file)
                if os.path.getsize(file_path) > 0:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        keys.update(data.keys())
    return list(keys)

# tmp_dirs =['/home/jiayu/result_llvmtuner_17/cBench/']
# final_keys = set()
# for directory in tmp_dirs:
#     keys = merge_keys(directory)
#     for key in transform_keys:
#         if key in keys:
#             final_keys.add(key)

#     # for key in keys:
#     #     if key not in transform_keys:
#     #         print(key)
# final_keys = sorted(list(final_keys))
# print(final_keys)
# print(len(final_keys))
# final_types = [x.split('.')[0] for x in final_keys]

# for subdir in subdirs:
#     directory = os.path.join(llvm_dir, subdir)
#     if os.path.isdir(directory):
#         f_list = os.listdir(directory)
#         for f in f_list:
#             fileroot,fileext = os.path.splitext(f)
#             if fileext == '.cpp' and f != 'EntryExitInstrumentater.cpp':#366个
#                 # print(os.path.join(directory, f))
#                 with open(os.path.join(directory, f), 'r') as file:
#                     data = file.read()
#                 info = re.findall('#define\s*DEBUG_TYPE\s*(.*?)\n', data, re.DOTALL)
#                 # info = re.findall(r'#define DEBUG_TYPE "(.*?)"', data, re.DOTALL)
#                 # assert len(info)<=1, {os.path.join(directory, f):info}
#                 types=[]
#                 for x in info:
#                     if x.startswith('"'):
#                         x=x.replace('"','')
#                     else:
#                         x_list = re.findall(f'#define\s*{x}\s*"(.*?)"', data, re.DOTALL)
#                         assert len(x_list) ==1, os.path.join(directory, f)
#                         x =x_list[0]
#                     llvm_debug_types.add(x)
#                     types.append(x)
#                 # if len(info)>1:
#                 #     print({os.path.join(directory, f):info})
#                 # if len(info)==1:
#                 #     llvm_debug_types.add(info[0])
#                 aa = re.findall(r'STATISTIC\s*\((.*?),\s*(.*?)\);\n', data, re.DOTALL)
#                 # aa = re.findall('STATISTIC\s*\((.*)\);\n', data)#\s*"(A-Za-z\s0-9]*?)"\)
#                 for xx in aa:
#                     if types[0] in final_types:
#                         print(types[0], xx)

# features after human check 
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

if __name__ == '__main__':
    pass_stats_keys = []
    for key in features:
        fks = features[key].split()
        for fk in fks:
            pass_stats_keys.append(key+'.'+fk)
    print(sorted(pass_stats_keys))
    print(len(pass_stats_keys))
    
#1. 明确多模块的确有效果，但是搜索代价过高，并且分配budget是一个问题
#2. 程序对pass的反应可以体现potential
#3. 利用potential可以帮助提升搜索效率
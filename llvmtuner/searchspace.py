# -*- coding: utf-8 -*-
"""
Created on Fri Feb 11 00:12:22 2022

@author: jiayu
"""

import subprocess
import os
from llvmtuner import globalvar

analysis_passes=['-callgraph','-lcg','-module-summary','-no-op-module','-profile-summary','-stack-safety','-verify','-pass-instrumentation','-asan-globals-md','-inline-advisor','-ir-similarity','-no-op-cgscc','-fam-proxy', '-pass-instrumentation','-aa','-assumptions','-block-freq','-branch-prob','-domtree','-postdomtree','-demanded-bits','-domfrontier','-func-properties','-loops','-lazy-value-info','-da','-inliner-size-estimator','-memdep','-memoryssa','-phi-values','-regions','-no-op-function','-opt-remark-emit','-scalar-evolution','-stack-safety-local','-targetlibinfo','-basicaa','-targetir','-pass-instrumentation','-basic-aa','-cfl-anders-aa','-cfl-steens-aa','-objc-arc-aa','-scev-aa','-scoped-noalias-aa','-tbaa','-no-op-loop','-access-info','-ddg','-iv-users','-pass-instrumentation','-transform-warning','-domtree','-profile-summary-info','-scalar-evolution','-lcssa-verification','-lazy-block-freq','-demanded-bits','-basiccg', '-loop-accesses','-globals-aa','-lazy-branch-prob','-opt-remark-emitter','-tti','-tbaa','-scoped-noalias', '-scoped-noalias-aa','-assumption-cache-tracker','-targetlibinfo','-verify','-lazy-block-freq']

def default_space():
    cmd='llvm-as < /dev/null | opt -enable-new-pm=0 -O3 -disable-output -debug-pass=Arguments 2> O3_debug_passes.txt'
    # cmd='llvm-as < /dev/null | opt -O3 -disable-output -debug-pass=Arguments 2> O3_debug_passes.txt'
    subprocess.run(cmd, shell=True)
    with open('O3_debug_passes.txt', 'r') as f:
        string=f.read()
    O3_seq=string.split()
    O3_seq=[x for x in O3_seq if x != 'Pass' and x != 'Arguments:']    
    O3_trans_seq=[x for x in O3_seq if x not in analysis_passes]
    # print('O3 seq',O3_trans_seq)
    other_passes='-attributor -break-crit-edges -loop-data-prefetch -loop-fusion -loop-reduce -loop-predication -loop-interchange -loop-simplifycfg -loop-unroll-and-jam -lowerinvoke -mergefunc -partial-inliner -sink -slsr -always-inline'.split()
    passes=list(set(O3_trans_seq + other_passes))
    # # print('O3 seq length:',len(O3_trans_seq), 'O3 transform pass number:',len(O3_trans_passes))
    # os.remove('O3_debug_passes.txt')
    # passes = sorted(passes)
    
    # passes=['-adce', '-aggressive-instcombine', '-alignment-from-assumptions', '-always-inline', '-argpromotion', '-attributor', '-barrier', '-bdce', '-break-crit-edges', '-called-value-propagation', '-callsite-splitting', '-constmerge', '-correlated-propagation', '-deadargelim', '-div-rem-pairs', '-dse', '-early-cse', '-early-cse-memssa', '-ee-instrument', '-elim-avail-extern', '-float2int', '-forceattrs', '-functionattrs', '-globaldce', '-globalopt', '-gvn', '-indvars', '-inferattrs', '-inline', '-instcombine', '-instsimplify', '-ipsccp', '-jump-threading', '-lcssa', '-libcalls-shrinkwrap', '-licm', '-loop-data-prefetch', '-loop-deletion', '-loop-distribute', '-loop-fusion', '-loop-idiom', '-loop-interchange', '-loop-load-elim', '-loop-predication', '-loop-reduce', '-loop-rotate', '-loop-simplify', '-loop-simplifycfg', '-loop-sink', '-loop-unroll', '-loop-unroll-and-jam', '-loop-unswitch', '-loop-vectorize', '-lower-constant-intrinsics', '-lower-expect', '-lowerinvoke', '-mem2reg', '-memcpyopt', '-mergefunc', '-mldst-motion', '-partial-inliner', '-pgo-memop-opt', '-prune-eh', '-reassociate', '-rpo-functionattrs', '-sccp', '-simplifycfg', '-sink', '-slp-vectorizer', '-speculative-execution', '-sroa', '-strip-dead-prototypes', '-tailcallelim']
    
    # passes_Cbench=['-adce', '-argpromotion', '-barrier', '-bdce', '-break-crit-edges', '-called-value-propagation', '-constmerge', '-dse', '-early-cse', '-early-cse-memssa', '-ee-instrument', '-elim-avail-extern', '-functionattrs', '-globalopt', '-gvn', '-indvars', '-inferattrs', '-inline', '-instcombine', '-ipsccp', '-jump-threading', '-licm', '-loop-fusion', '-loop-idiom', '-loop-reduce', '-loop-rotate', '-loop-simplifycfg', '-loop-unroll', '-loop-unswitch', '-loop-vectorize', '-mem2reg', '-reassociate', '-separate-const-offset-from-gep', '-simplifycfg', '-sink', '-slp-vectorizer', '-slsr', '-sroa', '-strip-dead-prototypes', '-tailcallelim']#'-separate-const-offset-from-gep', '-slsr', 
    # for x in passes_Cbench:
    #     if x not in passes:
    #         print(x)
    # passes = passes + passes_Cbench
    passes = sorted(set(passes))
    return passes,O3_trans_seq


def compilergym_space():  
    passes=['-add-discriminators', '-adce', '-aggressive-instcombine', '-alignment-from-assumptions', '-always-inline', '-argpromotion', '-attributor', '-barrier', '-bdce', '-break-crit-edges', '-simplifycfg', '-callsite-splitting', '-called-value-propagation', '-canonicalize-aliases', '-consthoist', '-constmerge', '-constprop', '-coro-cleanup', '-coro-early', '-coro-elide', '-coro-split', '-correlated-propagation', '-cross-dso-cfi', '-deadargelim', '-dce', '-die', '-dse', '-reg2mem', '-div-rem-pairs', '-early-cse-memssa', '-elim-avail-extern', '-ee-instrument', '-flattencfg', '-float2int', '-forceattrs', '-inline', '-insert-gcov-profiling', '-gvn-hoist', '-gvn', '-globaldce', '-globalopt', '-globalsplit', '-guard-widening', '-hotcoldsplit', '-ipconstprop', '-ipsccp', '-indvars', '-irce', '-infer-address-spaces', '-inferattrs', '-inject-tli-mappings', '-instsimplify', '-instcombine', '-instnamer', '-jump-threading', '-lcssa', '-licm', '-libcalls-shrinkwrap', '-load-store-vectorizer', '-loop-data-prefetch', '-loop-deletion', '-loop-distribute', '-loop-fusion', '-loop-guard-widening', '-loop-idiom', '-loop-instsimplify', '-loop-interchange', '-loop-load-elim', '-loop-predication', '-loop-reroll', '-loop-rotate', '-loop-simplifycfg', '-loop-simplify', '-loop-sink', '-loop-reduce', '-loop-unroll-and-jam', '-loop-unroll', '-loop-unswitch', '-loop-vectorize', '-loop-versioning-licm', '-loop-versioning', '-loweratomic', '-lower-constant-intrinsics', '-lower-expect', '-lower-guard-intrinsic', '-lowerinvoke', '-lower-matrix-intrinsics', '-lowerswitch', '-lower-widenable-condition', '-memcpyopt', '-mergefunc', '-mergeicmps', '-mldst-motion', '-sancov', '-name-anon-globals', '-nary-reassociate', '-newgvn', '-pgo-memop-opt', '-partial-inliner', '-partially-inline-libcalls', '-post-inline-ee-instrument', '-functionattrs', '-mem2reg', '-prune-eh', '-reassociate', '-redundant-dbg-inst-elim', '-rpo-functionattrs', '-rewrite-statepoints-for-gc', '-sccp', '-slp-vectorizer', '-sroa', '-scalarizer', '-separate-const-offset-from-gep', '-simple-loop-unswitch', '-sink', '-speculative-execution', '-slsr', '-strip-dead-prototypes', '-strip-debug-declare', '-strip-nondebug', '-strip', '-tailcallelim', '-mergereturn']
    return passes

if __name__ == "__main__":
    print(default_space())
    print(len(default_space()))
    # print(globalvar.get_value('compilergym_pass
    
# compilergym_unuseful_passes = '-add-discriminators'
# compilergym_passes = '-add-discriminators'




# with open('llvm10_all_passes.txt', 'r',encoding="utf-8") as f:
#     string=f.read()
#     all_passes=string.split('\n')
#     all_passes=[x for x in all_passes if x !='' and x[0] == '-']



# O3_trans_seq=[x for x in O3_seq if x not in analysis_passes]
# print(len(O3_seq),len(O3_trans_seq), len(set(O3_trans_seq)))
# with open('O3_trans_seq.txt', 'w') as f:
#     f.write(' '.join(O3_trans_seq))
# O3_trans_passes=list(set(O3_trans_seq))
# with open('O3_trans_passes.txt', 'w') as f:
#     f.write(' '.join(O3_trans_passes))
# with open('O3_trans_seq.txt', 'r') as f:
#     tmp = f.read()
#     O3_seq = tmp.split()
# print(O3_seq)
# with open('O3_trans_passes.txt', 'r') as f:
#     tmp = f.read()
#     O3_passes = tmp.split()
# print(O3_passes)


# print(set(O3_trans_seq))
# # tt='-sroa -globalopt -jump-threading -loop-unswitch -instcombine -loop-unroll'.split()
# # for x in O3_trans_seq:
# #     if x == tt[0]:
# #         tt.pop(0)
# #         print(tt)
# #         if tt == []:
# #             break

        
# # y=["-sroa", "-globalopt","-jump-threading","-loop-unswitch",
# #             "-ipsccp",
# #             "-instcombine",
# #             "-loop-unroll",
# #             "-attributor","-reassociate",
# #             "-instcombine",
# #             "-strip",
# #             "-mem2reg","-globalopt",
# #             "-mem2reg",
# #             "-reassociate",
# #             "-tailcallelim","-instcombine",
# #             "-sroa",
# #             "-jump-threading",
# #             "-loop-idiom",
# #             "-loop-deletion",
# #             "-sroa",
# #             "-tailcallelim"]

# # for x in y:
# #     if x not in O3_seq:
# #         print(x)

# # kkk='-loop-reroll -loop-unroll -unroll-allow-partial'

# #llvm10='-ee-instrument -simplifycfg -sroa -early-cse -lower-expect -forceattrs -inferattrs -callsite-splitting -ipsccp -called-value-propagation -attributor -globalopt -mem2reg -deadargelim -basicaa -instcombine -simplifycfg -prune-eh -inline -functionattrs -argpromotion -sroa -basicaa -early-cse-memssa -speculative-execution -jump-threading -correlated-propagation -simplifycfg -aggressive-instcombine -basicaa -instcombine -libcalls-shrinkwrap -pgo-memop-opt -basicaa -tailcallelim -simplifycfg -reassociate -loop-simplify -lcssa -basicaa -loop-rotate -licm -loop-unswitch -simplifycfg -basicaa -instcombine -loop-simplify -lcssa -indvars -loop-idiom -loop-deletion -loop-unroll -mldst-motion -gvn -basicaa -memcpyopt -sccp -bdce -instcombine -jump-threading -correlated-propagation -basicaa -dse -loop-simplify -lcssa -licm -adce -simplifycfg -basicaa -instcombine -barrier -elim-avail-extern -rpo-functionattrs -globalopt -globaldce -float2int -lower-constant-intrinsics -loop-simplify -lcssa -basicaa -loop-rotate -loop-distribute -basicaa -loop-vectorize -loop-simplify -loop-load-elim -basicaa -instcombine -simplifycfg -basicaa -slp-vectorizer -instcombine -loop-simplify -lcssa -loop-unroll -instcombine -loop-simplify -lcssa -licm -alignment-from-assumptions -strip-dead-prototypes -globaldce -constmerge -loop-simplify -lcssa -basicaa -loop-sink -instsimplify -div-rem-pairs -simplifycfg'.split()
# #
# #llvm12='-ee-instrument -simplifycfg -sroa -early-cse -lower-expect -annotation2metadata -forceattrs -inferattrs -callsite-splitting -ipsccp -called-value-propagation -globalopt -mem2reg -deadargelim -instcombine -simplifycfg -prune-eh -inline -openmpopt -function-attrs -argpromotion -sroa -early-cse-memssa -speculative-execution -jump-threading -correlated-propagation -simplifycfg -aggressive-instcombine -instcombine -libcalls-shrinkwrap -pgo-memop-opt -tailcallelim -simplifycfg -reassociate -loop-simplify -lcssa -loop-rotate -licm -loop-unswitch -simplifycfg -instcombine -loop-simplify -lcssa -loop-idiom -indvars -loop-deletion -loop-unroll -sroa -mldst-motion -gvn -memcpyopt -sccp -bdce -instcombine -jump-threading -correlated-propagation -adce -dse -loop-simplify -lcssa -licm -simplifycfg -instcombine -barrier -elim-avail-extern -rpo-function-attrs -globalopt -globaldce -float2int -lower-constant-intrinsics -loop-simplify -lcssa -loop-rotate -loop-distribute -inject-tli-mappings -loop-vectorize -loop-simplify -loop-load-elim -instcombine -simplifycfg -inject-tli-mappings -slp-vectorizer -vector-combine -instcombine -loop-simplify -lcssa -loop-unroll -instcombine -loop-simplify -lcssa -licm -alignment-from-assumptions -strip-dead-prototypes -globaldce -constmerge -cg-profile -loop-simplify -lcssa -loop-sink -instsimplify -div-rem-pairs -simplifycfg -annotation-remarks'.split()
# #print('\n')
# #diff=set(llvm10)^set(llvm12)
# #print(set(llvm10))

# llvm12_O3_passes=['-lower-expect', '-aggressive-instcombine', '-forceattrs', '-loop-unswitch', '-prune-eh', '-strip-dead-prototypes', '-argpromotion', '-ipsccp', '-div-rem-pairs', '-openmpopt', '-called-value-propagation', '-pgo-memop-opt', '-constmerge', '-libcalls-shrinkwrap', '-speculative-execution', '-loop-simplify', '-mldst-motion', '-adce', '-callsite-splitting', '-indvars', '-loop-unroll', '-dse', '-bdce', '-vector-combine', '-globaldce', '-inject-tli-mappings', '-lcssa', '-gvn', '-slp-vectorizer', '-loop-vectorize', '-lower-constant-intrinsics', '-sroa', '-early-cse-memssa', '-loop-deletion', '-deadargelim', '-licm', '-globalopt', '-mem2reg', '-jump-threading', '-correlated-propagation', '-simplifycfg', '-float2int', '-cg-profile', '-ee-instrument', '-barrier', '-function-attrs', '-reassociate', '-instcombine', '-alignment-from-assumptions', '-loop-idiom', '-early-cse', '-tailcallelim', '-loop-rotate', '-annotation-remarks', '-memcpyopt', '-loop-distribute', '-sccp', '-loop-sink', '-annotation2metadata', '-inline', '-inferattrs', '-loop-load-elim', '-instsimplify', '-rpo-function-attrs', '-elim-avail-extern']
# llvm10_O3_passes=['-prune-eh', '-barrier', '-early-cse', '-globalopt', '-loop-rotate', '-simplifycfg', '-correlated-propagation', '-deadargelim', '-loop-simplify', '-loop-unswitch', '-loop-load-elim', '-alignment-from-assumptions', '-bdce', '-elim-avail-extern', '-constmerge', '-callsite-splitting', '-functionattrs', '-licm', '-loop-sink', '-called-value-propagation', '-memcpyopt', '-float2int', '-dse', '-div-rem-pairs', '-lcssa', '-adce', '-loop-deletion', '-gvn', '-indvars', '-sroa', '-lower-constant-intrinsics', '-reassociate', '-libcalls-shrinkwrap', '-loop-distribute', '-jump-threading', '-loop-idiom', '-loop-unroll', '-aggressive-instcombine', '-mem2reg', '-loop-vectorize', '-speculative-execution', '-pgo-memop-opt', '-instcombine', '-rpo-functionattrs', '-ee-instrument', '-instsimplify', '-inferattrs', '-inline', '-tailcallelim', '-globaldce', '-slp-vectorizer', '-sccp', '-mldst-motion', '-ipsccp', '-argpromotion', '-lower-expect', '-strip-dead-prototypes', '-attributor', '-early-cse-memssa', '-forceattrs']

# x=[x for x in llvm10_O3_passes if x not in llvm12_O3_passes]
# print(x)

other = ['502.gcc_r','525.x264_r','531.deepsjeng_r','557.xz_r']
test=['505.mcf_r','520.omnetpp_r', '541.leela_r','544.nab_r']
train=['510.parest_r','511.povray_r','519.lbm_r']

different = ['523.xalancbmk_r','526.blender_r']
analyze = ['538.imagick_r','508.namd_r','500.perlbench_r']

merged_list = train + test + other + different + analyze
print(sorted(merged_list))
print(len(merged_list))
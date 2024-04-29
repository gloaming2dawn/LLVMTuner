import re

with open('/home/jiayu/result_llvmtuner_17/cBench/telecom_gsm/cost_model/pmu_O3.txt', 'r') as f:
    text = f.read()

features = {}

lines = text.strip().split('\n')
for line in lines:
    match = re.search(r'(\d+(?:,\d+)*)\s+(\w+(?:-\w+)*)', line)
    if match:
        value = match.group(1).replace(',', '')
        key = match.group(2)
        features[key] = int(value)

pmu_events = 'branch-misses,cache-misses,cache-references,cpu-cycles,instructions,cpu-clock,L1-dcache-load-misses,L1-dcache-loads,L1-dcache-store-misses,L1-dcache-stores,branch-load-misses,branch-loads'.split(',')
features = {k: features[k] for k in pmu_events}
print(features)
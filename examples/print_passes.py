import llvmtuner
from llvmtuner.searchspace import default_space
passes, passes_clear, pass2kind, O3_trans_seq=default_space()
print(passes_clear)
print(len(passes_clear))
print(passes)
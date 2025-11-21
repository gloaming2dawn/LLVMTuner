#!/bin/bash
version=17.0.6
git clone https://github.com/llvm/llvm-project.git
cd llvm-project
git checkout llvmorg-${version} || exit
mkdir build-${version}
cd build-${version}
cmake -G Ninja -DCMAKE_INSTALL_PREFIX=~/llvm${version} -DLLVM_ENABLE_PROJECTS='clang;polly;lld;compiler-rt' -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=ON ../llvm
ninja
ninja install
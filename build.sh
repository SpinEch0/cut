git submodule init
git submodule update
cd llvm
git apply ../patch/0001-add-casefind-checker.patch 

cmake -DLLVM_ENABLE_PROJECTS=clang -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_Z3_SOLVER=true  -G "Unix Makefiles" llvm -B build

cd build && make -j8

cd ../..

poetry build

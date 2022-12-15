# A C unit test case generator

## Build

```
git submodule init
git submodule update
cd llvm
git apply ../patch/0001-add-casefind-checker.patch

cmake -DLLVM_ENABLE_PROJECTS=clang -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_Z3_SOLVER=true  -G "Unix Makefiles" llvm -B build

cd build && make -j8

cd ../..

poetry build
```
Install clang and cut.whl, then we can generate cases automaticly.

## Usage

Usage is simillar as codechecker.
```
cut -g "your compile commands"
```
As a example, in cut root directory running below commands:
```
cut -g "gcc -c test.c"
```
It output test.c_test_max.c file with two cases:
```C
void test_max_1()                       |int max(int a, int  b) {
{                                       |  return a > b ? a : b;
  int a;                                |}
  int b;                                |~                                      
  b = 0x00000000;                       |~                                      
  a = 0x00000001;                       |~                                      
  max(a, b);                            |~                                      
  myfree();                             |~                                      
}                                       |~                                      
                                        |~                                      
void test_max_2()                       |~                                      
{                                       |~                                      
  int a;                                |~                                      
  int b;                                |~                                      
  b = 0x00000000;                       |~                                      
  a = 0x80000001;                       |~                                      
  max(a, b);                            |~                                      
  myfree();                             |~                                      
}  
```

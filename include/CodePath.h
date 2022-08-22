#ifndef CODEPATH_H
#define CODEPATH_H
#include "llvm/Pass.h"
#include "llvm/IR/PassManager.h"
#include "llvm/ADT/PostOrderIterator.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Module.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/IR/InstIterator.h"
#include "llvm/IR/Instruction.h"
#include "llvm/IR/DebugInfo.h"
#include "llvm/IR/InstrTypes.h"
#include "llvm/IR/AssemblyAnnotationWriter.h"
#include "llvm/Support/FormattedStream.h"
#include "llvm/IR/Constants.h"
#include "llvm/Analysis/CFGPrinter.h"
#include <ostream>
#include <fstream>
#include <iostream>
#include <stdlib.h>

using namespace llvm;

class CodePath {
 public:
  CodePath() {};
  void Push(BasicBlock *node) {
    nodes.push_back(node);
  }
  void Print() {
    errs() << "\n\nstart";
    for (auto i : nodes) {
      errs() << "->" << i->getName();
    }
  }
  std::vector<BasicBlock *> nodes;
};
#endif

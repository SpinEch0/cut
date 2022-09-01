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
#include "AnalyzeGraph.h"

using namespace llvm;

// LLVM uses the address of this static member to identify the pass, so the
// initialization value is unimportant.
char AnalyzeBBGraph::ID = 0;
// Register this pass to be used by language front ends.
// This allows this pass to be called using the command:
//    clang -c -Xclang -load -Xclang ./FunctionInfo.so loop.c
static void registerMyPass(const PassManagerBuilder &Builder,
       legacy::PassManagerBase &PM) {
  PM.add(new AnalyzeBBGraph());
}

void visitBasicBlock(std::vector<CodePath> &paths, CodePath temp_path, std::set<llvm::BasicBlock *> visitedBlocks, llvm::BasicBlock *BB)
{
  // errs() << "\n visit block " << BB->getName() << "\n";
  const Instruction *term = BB->getTerminator();
  // errs() << "\n inst name " << term->getOpcodeName() << "\n"; 
  visitedBlocks.insert(BB);
  temp_path.Push(BB);
  // for each successor, from the last to the first, call visitBasicBlock in that successor
  unsigned int idx = term->getNumSuccessors();
  if (idx == 0) {
    paths.push_back(temp_path);
  } else {
    while (idx != 0) {
      --idx;
      if (visitedBlocks.find(term->getSuccessor(idx)) == visitedBlocks.end()) {
        visitBasicBlock(paths, temp_path, visitedBlocks, term->getSuccessor(idx));
      } else {
        paths.push_back(temp_path);
      }
    }
  }
}

bool AnalyzeBBGraph::runOnFunction(Function &F) {
  std::set<llvm::BasicBlock*> visited;
  CodePath temp_path;
  paths.clear();
  llvm::BasicBlock &entryBlock = F.getEntryBlock();
  visitBasicBlock(paths, temp_path, visited, &entryBlock);
  errs() << "\n\n============== function paths " << F.getName() << "\n";
  for (auto &arg : F.args()) {
    if (!arg.user_empty())
      errs() << "args " << arg.getName() << "\n";
  }
  for (auto path : paths) {
    path.Print();
  }

  return false;
}

// static RegisterStandardPasses
//     RegisterMyPass(PassManagerBuilder::EP_EarlyAsPossible,
//             registerMyPass);

// Register the pass name to allow it to be called with opt:
//    clang -c -g -emit-llvm loop.c
//    opt -load ./ModuleInfo.so -module-info loop.bc > /dev/null
// See http://llvm.org/releases/3.4/docs/WritingAnLLVMPass.html#running-a-pass-with-opt for more info.
// RegisterPass<AnalyzeBBGraph> X("path", "module Information");


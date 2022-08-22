#include "llvm/AsmParser/Parser.h"
#include "llvm/Support/SourceMgr.h"
#include "llvm/IRReader/IRReader.h"
#include "llvm/Pass.h"
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
#include <fstream>

#include "AnalyzeGraph.h"

using namespace llvm;

int main(int argc, char **argv) {

  // Parse the input LLVM IR file into a module.
  SMDiagnostic Err;
  LLVMContext Context;

  std::unique_ptr<Module> Mod(parseIRFile(argv[1], Err, Context));
  if (!Mod) {
    Err.print(argv[0], errs());
    return 1;
  }

  // Create a pass manager and fill it with the passes we want to run.
  legacy::PassManager PM;
  PM.add(new AnalyzeBBGraph());
  PM.run(*Mod);

  return 0;
}

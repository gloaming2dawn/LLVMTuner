//=============================================================================
// FILE:
//    HelloWorld.cpp
//
// DESCRIPTION:
//    Visits all functions in a module, prints their names and the number of
//    arguments via stderr. Strictly speaking, this is an analysis pass (i.e.
//    the functions are not modified). However, in order to keep things simple
//    there's no 'print' method here (every analysis pass should implement it).
//
// USAGE:
//    1. Legacy PM
//      opt -load libHelloWorld.dylib -legacy-hello-world -disable-output `\`
//        <input-llvm-file>
//    2. New PM
//      opt -load-pass-plugin=libHelloWorld.dylib -passes="hello-world" `\`
//        -disable-output <input-llvm-file>
//
//
// License: MIT
//=============================================================================
//#include "llvm/IR/LegacyPassManager.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/ADT/MapVector.h"
#include "llvm/ADT/PostOrderIterator.h"
#include "llvm/Analysis/LoopInfo.h"
#include "llvm/IR/Type.h"
#include "llvm/Transforms/Scalar.h"
#include "llvm/IR/DebugLoc.h"
#include "llvm/IR/DebugInfo.h"
#include "llvm/IR/DebugInfoMetadata.h"
#include "llvm/Analysis/BlockFrequencyInfo.h"
#include "llvm/Analysis/BranchProbabilityInfo.h"
#include "llvm/Pass.h"
#include "llvm/IR/PassManager.h"
#include "llvm/IR/Attributes.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/IR/Type.h"
#include "llvm/IR/GlobalVariable.h"
#include "llvm/Support/CommandLine.h"



#include <list>
#include <string>
#include <vector>
#include <stdexcept>
#include <iostream>
#include <fstream>
#include <iomanip>

#include <nlohmann/json.hpp>
#include<boost/tokenizer.hpp>

using json = nlohmann::json;
using namespace llvm;
static cl::opt<std::string> JsonFile("jsonfile", cl::init(""), cl::Hidden,
                        cl::value_desc("filename"),
                        cl::desc("Specify the path of dict json data file."));

#define DIM 87
using Vector = llvm::SmallVector<double, DIM>;
std::vector<std::string> opcode_keys = {"add", "alloca", "and", "ashr", "atomicrmw", "bitcast", "br", "call", "cmpxchg", "extractelement", "extractvalue", "fadd", "fcmp", "fdiv", "fence", "fmul", "fneg", "fpext", "fptosi", "fptoui", "fptrunc", "freeze", "fsub",  "getelementptr", "icmp", "insertelement", "insertvalue", "inttoptr", "invoke", "landingpad", "load", "lshr", "mul", "or", "phi", "ptrtoint", "resume", "ret", "sdiv", "select", "sext", "shl", "shufflevector", "sitofp", "srem", "store", "sub", "switch", "trunc", "udiv", "uitofp", "unreachable", "urem", "xor", "zext"};
std::vector<std::string> type_keys = {"floatTy", "integerTy", "pointerTy", "functionTy", "structTy", "vectorTy", "voidTy", "arrayTy","emptyTy", "labelTy", "tokenTy", "metadataTy"};
std::vector<std::string> operand_keys = {"constant","function","pointer","variable"};

std::vector<std::string> keys = {"add", "alloca", "and", "ashr", "atomicrmw", "bitcast", "br", "call", "cmpxchg", "extractelement", "extractvalue", "fadd", "fcmp", "fdiv", "fence", "fmul", "fneg", "fpext", "fptosi", "fptoui", "fptrunc", "freeze", "fsub",  "getelementptr", "icmp", "insertelement", "insertvalue", "inttoptr", "invoke", "landingpad", "load", "lshr", "mul", "or", "phi", "ptrtoint", "resume", "ret", "sdiv", "select", "sext", "shl", "shufflevector", "sitofp", "srem", "store", "sub", "switch", "trunc", "udiv", "uitofp", "unreachable", "urem", "xor", "zext",        "floatTy", "integerTy", "pointerTy", "functionTy", "structTy", "vectorTy", "voidTy", "arrayTy","emptyTy", "labelTy", "tokenTy", "metadataTy",       "constant","function","pointer","variable",        "ArgMemOnly", "ReadNone", "ReadOnly", "WriteOnly", "NoAlias", "NonNullReturn", "NoRecurse", "NoUnwind", "NoFree", "WillReturn", "NoSync",     		"NoCapture", "Returned", "ReadNoneArg", "ReadOnlyArg", "WriteOnlyArg"};//here include opcodes, types, operands and attributes
std::map<std::string, Vector> opcMap;


Vector getValue(std::string key) {
  Vector vec;
  if (opcMap.find(key) == opcMap.end()) {
    errs() << "cannot find key in map : " << key << "\n";
	throw std::invalid_argument( "cannot find key in map" );
  }
  else
    vec = opcMap[key];
  return vec;
}

/*
void scaleVector(Vector &vec, float factor) {
  for (unsigned i = 0; i < vec.size(); i++) {
    vec[i] = vec[i] * factor;
  }
}
*/


//-----------------------------------------------------------------------------
// HelloWorld implementation
//-----------------------------------------------------------------------------
// No need to expose the internals of the pass to the outside world - keep
// everything in an anonymous namespace.
namespace {

// This method implements what the pass does
void visitor(Function &F) {
    errs() << "(llvm-tutor) Hello from: "<< F.getName() << "\n";
    errs() << "(llvm-tutor)   number of arguments: " << F.arg_size() << "\n";
}




struct HelloWorld : PassInfoMixin<HelloWorld> {
  // Main entry point, takes IR unit to run the pass on (&F) and the
  // corresponding pass manager (to be queried if need be)
  

 	PreservedAnalyses run(Module &M, ModuleAnalysisManager &MAM) {
		json j;
		uint64_t total_counts=0;
		FunctionAnalysisManager &FAM =MAM.getResult<FunctionAnalysisManagerModuleProxy>(M).getManager();

		// for (auto gv_iter = M.global_begin(); gv_iter != M.global_end(); gv_iter++) {
		// 	/* GLOBAL DATA INFO*/
        //     GlobalVariable *gv = &*gv_iter;
		// 	auto Attrs = gv->getAttributes();
		// 	Attrs.dump();
		// 	if (gv->isConstant()){
		// 		errs()<<"aaaaabbbbbb"<<"\n";
		// 	}
		// }
                   
	

		for (auto& F : M) {
			// DILocation *Loc;
			if (!F.isDeclaration()) {
				std::string attrs_str = F.getName().str() + "---";
				auto Attrs = F.getAttributes();
				for (unsigned i = Attrs.index_begin(), e = Attrs.index_end(); i != e; ++i) {
						if (Attrs.getAttributes(i).hasAttributes()){
							std::string str1 = Attrs.getAsString(i);
							attrs_str += std::to_string(i) + " => " + str1;
							// errs() << "  { " << std::to_string(i) + " --- " + str1 << " }\n";
						}
						
					}

				
				//auto *BFI = &FAM.getResult<BlockFrequencyAnalysis>(F);
				BlockFrequencyInfo BFI;
				BFI.calculate(F, FAM.getResult<BranchProbabilityAnalysis>(F), FAM.getResult<LoopAnalysis>(F));
				
				for (auto& B : F) {
					// errs() <<"========================"<<F.getName()<< B.getName()<<"\n";
					auto tmp = BFI.getBlockProfileCount(&B);
					uint64_t InstrCount;
					// InstrCount=tmp.getValue();
					if (tmp == None){
						InstrCount=0;
					}
					else
						InstrCount=tmp.getValue();

					auto BlockFreq = BFI.getBlockFreq(&B).getFrequency();
					// errs()<<"entry Freq:"  <<BFI.getEntryFreq()<< "\n";
					if (InstrCount !=0) { //if (InstrCount !=0)
						// errs() <<F.getName()<<"-%"<< B.getName() <<" "<< InstrCount << "\n";
					

						for (auto& I : B) {
							total_counts += InstrCount;
							// I.dump();
						}

					}

					
				}
			}	
		}

	//print final IR Vector
	// std::string res0= "";
	// for (auto v : IRVector) {
	// 	res0 += std::to_string(v) + "\t";
	// }
	// errs()<< res0 << "\n";

	


	
	// std::ofstream o("example.json");
	// o << std::setw(4) << j << std::endl;
	std::cout<<std::to_string(total_counts)<<'\n';

	// std::cout << std::setw(4) << j << std::endl;

    return PreservedAnalyses::all();
  }
  

  // Without isRequired returning true, this pass will be skipped for functions
  // decorated with the optnone LLVM attribute. Note that clang -O0 decorates
  // all functions with optnone.
  static bool isRequired() { return true; }
};

/*
// Legacy PM implementation
struct LegacyHelloWorld : public FunctionPass {
  static char ID;
  LegacyHelloWorld() : FunctionPass(ID) {}
  // Main entry point - the name conveys what unit of IR this is to be run on.
  bool runOnFunction(Function &F) override {
    visitor(F);
    // Doesn't modify the input unit of IR, hence 'false'
    return false;
  }
};
*/

} // namespace


//-----------------------------------------------------------------------------
// New PM Registration
//-----------------------------------------------------------------------------
llvm::PassPluginLibraryInfo getHelloWorldPluginInfo() {
  return {LLVM_PLUGIN_API_VERSION, "ir2dict", LLVM_VERSION_STRING,
          [](PassBuilder &PB) {
            PB.registerPipelineParsingCallback(
                [](StringRef Name, ModulePassManager &MPM,
                   ArrayRef<PassBuilder::PipelineElement>) {
                  if (Name == "ir2dict") {
                    MPM.addPass(HelloWorld());
                    return true;
                  }
                  return false;
                });
          }};
}

// This is the core interface for pass plugins. It guarantees that 'opt' will
// be able to recognize HelloWorld when added to the pass pipeline on the
// command line, i.e. via '-passes=hello-world'
extern "C" LLVM_ATTRIBUTE_WEAK ::llvm::PassPluginLibraryInfo
llvmGetPassPluginInfo() {
  return getHelloWorldPluginInfo();
}

/*
//-----------------------------------------------------------------------------
// Legacy PM Registration
//-----------------------------------------------------------------------------
// The address of this variable is used to uniquely identify the pass. The
// actual value doesn't matter.
char LegacyHelloWorld::ID = 0;

// This is the core interface for pass plugins. It guarantees that 'opt' will
// recognize LegacyHelloWorld when added to the pass pipeline on the command
// line, i.e.  via '--legacy-hello-world'
static RegisterPass<LegacyHelloWorld>
    X("ir2dict", "Hello World Pass",
      true, // This pass doesn't modify the CFG => true
      false // This pass is not a pure analysis pass => false
    );
	*/

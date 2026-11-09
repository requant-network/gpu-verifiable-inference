// Original Requant Network test bridge (MIT); included FlashProve kernels retain Apache-2.0 notices.
#include <cuda_runtime.h>
#include <stdexcept>
#include <string>
#include "common/index_guard.cuh"
#include "weights_blocks/blocks.h"

// Field layout from FlashProve forward_moe.cuh; only routing inputs are needed by this isolated kernel.
struct MoeTables {
 int T,NE,S;int *cnt,*sbase,*rbase,*rank_of,*tok_of,*te,*tc,*tr;
};
static void checked(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
#define CK(x) checked(x)
#define CK_ATTRIBUTE(...) checked(cudaFuncSetAttribute(__VA_ARGS__))
#include "weights_blocks/experts_in_one_launch.cuh"
#if FLASH_EXPERT_COMPACT != 1
#error This bridge validates the explicitly selected compact fused path
#endif

static thread_local std::string last_error;
template<int NL> static void launch(int rows,int K,int T,int NE,int S,int q5,const unsigned char* weights,
 const float* gains,const signed char* planes,int* counts,int* slots,int* ranks,long long* out,cudaStream_t stream){
 MoeTables m{T,NE,S,counts,slots,ranks,nullptr,nullptr,nullptr,nullptr,nullptr};
 wb::Blocks b;b.bytes=weights;b.rows=rows;b.inputs=K;b.type=q5?wb::Q5_K:wb::Q4_K;b.gain=gains;b.scale=64.f;
 const int8_t* x[NL];for(int i=0;i<NL;i++)x[i]=planes+(size_t)i*S*K;
 pk_grouped_blocks<NL>(m,b,x,K,out,stream);
}
extern "C" const char* rq_expert_error(){return last_error.c_str();}
extern "C" int rq_expert_shared(int limbs,int slots){
 int input=66048+16*(limbs*slots*16+32),output=256*limbs*slots*4;
 return input>output?input:output;
}
extern "C" int rq_expert_run(int limbs,int rows,int K,int T,int NE,int S,int q5,const unsigned char* weights,
 const float* gains,const signed char* planes,int* counts,int* slots,int* ranks,long long* out,cudaStream_t stream){
 try{
  if(limbs<1||limbs>4||rows<=0||rows%128||K<=0||K%256||T<=0||NE<=0||S<T+64*NE)return 2;
  switch(limbs){
   case 1:launch<1>(rows,K,T,NE,S,q5,weights,gains,planes,counts,slots,ranks,out,stream);break;
   case 2:launch<2>(rows,K,T,NE,S,q5,weights,gains,planes,counts,slots,ranks,out,stream);break;
   case 3:launch<3>(rows,K,T,NE,S,q5,weights,gains,planes,counts,slots,ranks,out,stream);break;
   case 4:launch<4>(rows,K,T,NE,S,q5,weights,gains,planes,counts,slots,ranks,out,stream);break;
  }
  return 0;
 }catch(const std::exception& e){last_error=e.what();return 1;}
}

import json
import random
import argparse
from vllm import LLM, SamplingParams
import torch.distributed as dist
import gc
import multiprocessing.shared_memory as shared_memory
import warnings
from tqdm import tqdm
from ..template.synthesize_checklist_template import (
    EN_AGRI_SYSTEM_PROMPT, 
    EN_MEDICINE_SYSTEM_PROMPT,
    EN_LAW_SYSTEM_INSTRUCTION
)

random.seed(42)


def get_system_prompt(domain):
    domain_prompts = {
        "EN_AGRI": EN_AGRI_SYSTEM_PROMPT,
        "EN_MEDICINE": EN_MEDICINE_SYSTEM_PROMPT,
        "EN_LAW": EN_LAW_SYSTEM_INSTRUCTION
    }
    
    if domain not in domain_prompts:
        raise ValueError(f"Unknown domain: {domain}. Available domains: {list(domain_prompts.keys())}")
    
    return domain_prompts[domain]

def cleanup_llm_resources(llm):
    if hasattr(llm, 'engine') and hasattr(llm.engine, 'engine'):
        if hasattr(llm.engine.engine, 'scheduler'):
            llm.engine.engine.scheduler = None
        if hasattr(llm.engine.engine, 'worker_pool'):
            llm.engine.engine.worker_pool = None
    
    try:
        if dist.is_initialized():
            dist.destroy_process_group()
    except:
        pass
    
    try:
        for shm_name in shared_memory._shared_memory_names():
            try:
                shm = shared_memory.SharedMemory(name=shm_name, create=False)
                shm.close()
                shm.unlink()
            except Exception as e:
                warnings.warn(f"Failed to clean shared memory {shm_name}: {e}")
    except Exception:
        pass
    
    gc.collect()

def get_llm(model_path, tensor_parallel_size=8):
    llm = LLM(model=model_path, tensor_parallel_size=tensor_parallel_size)
    sampling_params = SamplingParams(temperature=0.7, top_p=0.8, top_k=20, max_tokens=16384, repetition_penalty=1.05, seed=42)
    return llm, sampling_params

def process_batch(batch, llm, sampling_params, domain):
    conversations = []
    
    # Get the appropriate system prompt based on domain
    system_prompt = get_system_prompt(domain)

    for hash_id, item in batch:
        question = item["question"]
        ground_truth = item["answer"]
        
        prompt = f"[Specific Question]\nQuestion: {question}\nAnswer: {ground_truth}"
        conversation = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        conversations.append(conversation)

    outputs = llm.chat(conversations, sampling_params)
    responses = [output.outputs[0].text for output in outputs]

    return responses

def synthesize_checklist(args):
    with open(args.input_file, "r", encoding="utf-8") as f:
        data = json.load(f) # dict
    
    # Handle test mode
    if args.test_mode:
        data_items = list(data.items())[:args.test_limit]
        data = dict(data_items)
    
    llm, sampling_params = get_llm(model_path=args.model_path, tensor_parallel_size=args.tensor_parallel_size)
    
    try:
        batches = [list(data.items())[i:i+args.batch_size] for i in range(0, len(data), args.batch_size)]
        
        progress_bar = tqdm(
            total=len(data),
            desc="synthesize rule",
            unit="item"
        )
        
        new_data = {}
        error_items = []
        skipped_count = 0
        
        for batch in batches:
            batch_results = process_batch(batch, llm, sampling_params, args.domain)
            
            for (hash_id, item), checklist in zip(batch, batch_results):
                try:
                    json.loads(checklist)
                    new_item = item.copy()
                    new_item["checklist"] = checklist
                    new_data[hash_id] = new_item
                except Exception as e:
                    error_item = {
                        "hash_id": hash_id,
                        "item": item,
                        "checklist": checklist,
                        "error": str(e)
                    }
                    error_items.append(error_item)
                    warnings.warn(f"Skipping item {hash_id}: Error processing checklist. Error: {e}")
                    skipped_count += 1

            progress_bar.update(len(batch))
        progress_bar.close()
        
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=4)
            
        if error_items:
            import os
            base_name = os.path.splitext(args.output_file)[0]
            extension = os.path.splitext(args.output_file)[1]
            error_file_path = f"{base_name}-errors{extension}"
            
            with open(error_file_path, "w", encoding="utf-8") as f:
                json.dump(error_items, f, ensure_ascii=False, indent=4)
            
            print(f"Saved {len(error_items)} error items to: {error_file_path}")
        
    finally:
        cleanup_llm_resources(llm)
        del llm
        gc.collect()

def parse_args():
    parser = argparse.ArgumentParser(description="Synthesize checklist for Q&A data")
    
    # Required arguments
    parser.add_argument("--input_file", type=str, required=True,
                        help="Path to input JSON file")
    parser.add_argument("--output_file", type=str, required=True,
                        help="Path to output JSON file")
    parser.add_argument("--model_path", type=str, required=True,
                        help="Path to the model")
    
    parser.add_argument("--domain", type=str, required=True,
                        choices=["EN_AGRI", "EN_MEDICINE", "EN_LAW"],
                        help="Domain for checklist synthesis (required)")
    
    # Optional arguments
    parser.add_argument("--test_mode", action="store_true",
                        help="Enable test mode")
    parser.add_argument("--test_limit", type=int, default=100,
                        help="Test mode limit (default: 100)")
    parser.add_argument("--batch_size", type=int, default=16,
                        help="Batch size (default: 16)")
    parser.add_argument("--tensor_parallel_size", type=int, default=8,
                        help="Tensor parallel size (default: 8)")
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    print(f"Synthesizing checklist for {args.input_file}")
    print(f"Output file: {args.output_file}")
    print(f"Domain: {args.domain}")
    print(f"Test mode: {args.test_mode}")
    if args.test_mode:
        print(f"Test limit: {args.test_limit}")
    
    synthesize_checklist(args)
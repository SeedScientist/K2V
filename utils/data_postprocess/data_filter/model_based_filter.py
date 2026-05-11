"""
Model-based data quality filtering using LLM evaluation
"""

from openai import OpenAI, AsyncOpenAI
import json
import os
import re
import asyncio
from datetime import datetime
from tqdm import tqdm
from typing import Dict, Tuple, Optional, List, Any
from concurrent.futures import ThreadPoolExecutor
import time
from vllm import LLM, SamplingParams
import logging
from ..template.model_based_filter_template import ENG_SYSTEM_PROMPT

DEFAULT_CONFIG = {
    "openai_api_key": "EMPTY",
    "openai_api_base": "http://localhost:8000/v1",
    "test_mode": False,  # If True, only process only first 100 items
    "test_limit": 100,
    "inference_mode": "offline",  # "async_api", or "offline"
    "batch_size": 16,  # Batch size for vLLM or async API
    "max_concurrency": 8,  # Max concurrent requests for async API
    "model_path": None,  # Local model path for vLLM
    "tensor_parallel_size": 8,  # Tensor parallel size for vLLM
}



def get_client(config: Optional[Dict] = None):
    """
    Create OpenAI client with configuration
    
    Args:
        config: Configuration dictionary, uses defaults if None
        
    Returns:
        OpenAI client instance
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    client = OpenAI(
        api_key=config.get("openai_api_key", DEFAULT_CONFIG["openai_api_key"]),
        base_url=config.get("openai_api_base", DEFAULT_CONFIG["openai_api_base"]),
    )
    return client

async def get_async_client(config: Optional[Dict] = None):
    """
    Create AsyncOpenAI client with configuration
    
    Args:
        config: Configuration dictionary, uses defaults if None
        
    Returns:
        AsyncOpenAI client instance
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    client = AsyncOpenAI(
        api_key=config.get("openai_api_key", DEFAULT_CONFIG["openai_api_key"]),
        base_url=config.get("openai_api_base", DEFAULT_CONFIG["openai_api_base"]),
    )
    return client

def extract_evaluation_fields(response_text: str) -> Dict:
    """
    Extract evaluation fields from the model response text
    
    Args:
        response_text: The response text from the model (JSON format)
        
    Returns:
        dict: Dictionary containing extracted fields
    """
    fields = {
        "is_high_quality": None,
        "quality_score": None,
        "reasoning": None,
        "low_quality_category": None
    }
    
    try:
        # First try to parse as JSON
        if response_text.strip().startswith('{') and response_text.strip().endswith('}'):
            json_data = json.loads(response_text.strip())
            fields["is_high_quality"] = json_data.get("is_high_quality")
            fields["quality_score"] = json_data.get("quality_score")
            fields["reasoning"] = json_data.get("reasoning")
            fields["low_quality_category"] = json_data.get("low_quality_category")
            return fields
        
        # If JSON parsing fails, try to extract JSON from text
        # Look for JSON block in the response
        json_match = re.search(r'\{[^{}]*"is_high_quality"[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            json_data = json.loads(json_str)
            fields["is_high_quality"] = json_data.get("is_high_quality")
            fields["quality_score"] = json_data.get("quality_score")
            fields["reasoning"] = json_data.get("reasoning")
            fields["low_quality_category"] = json_data.get("low_quality_category")
            return fields
        
        # Fallback to regex parsing for text format
        # Extract is_high_quality
        is_high_quality_match = re.search(r'is_high_quality["\']?\s*:\s*["\']?(true|false)["\']?', response_text, re.IGNORECASE)
        if is_high_quality_match:
            fields["is_high_quality"] = is_high_quality_match.group(1).lower() == "true"
        
        # Extract quality_score
        quality_score_match = re.search(r'quality_score["\']?\s*:\s*["\']?(\d+)["\']?', response_text)
        if quality_score_match:
            fields["quality_score"] = int(quality_score_match.group(1))
        
        # Extract reasoning
        reasoning_match = re.search(r'reasoning["\']?\s*:\s*["\']?(.*?)["\']?(?=,\s*["\']?\w+["\']?\s*:|$)', response_text, re.DOTALL)
        if reasoning_match:
            fields["reasoning"] = reasoning_match.group(1).strip().strip('"\'')
        
        # Extract low_quality_category
        category_match = re.search(r'low_quality_category["\']?\s*:\s*["\']?(FACTUAL_RECALL|AMBIGUOUS_ANSWER|LOGICALLY_UNSOUND|NONE)["\']?', response_text, re.IGNORECASE)
        if category_match:
            fields["low_quality_category"] = category_match.group(1).upper()
    
    except json.JSONDecodeError:
        # Silently handle JSON parsing errors, fields will remain None
        pass
    except Exception:
        # Silently handle other parsing errors, fields will remain None
        pass
    
    return fields

def calculate_evaluation_statistics(data: Dict) -> Dict:
    """
    Calculate evaluation statistics from processed data
    
    Args:
        data: The processed data dictionary
        
    Returns:
        Dictionary containing detailed evaluation statistics
    """
    # Calculate basic statistics
    total_items = len(data)
    high_quality_count = sum(1 for item in data.values() if item.get("is_high_quality") == True)
    low_quality_count = sum(1 for item in data.values() if item.get("is_high_quality") == False)
    failed_count = sum(1 for item in data.values() if item.get("is_high_quality") is None)
    
    # Quality score distribution
    quality_scores = [item.get("quality_score") for item in data.values() if item.get("quality_score") is not None]
    score_distribution = {i: quality_scores.count(i) for i in range(1, 6)}
    
    # Low quality category distribution
    low_quality_categories = [item.get("low_quality_category") for item in data.values() 
                            if item.get("low_quality_category") and item.get("low_quality_category") != "NONE"]
    category_distribution = {category: low_quality_categories.count(category) 
                           for category in ["FACTUAL_RECALL", "AMBIGUOUS_ANSWER", "LOGICALLY_UNSOUND"]}
    
    # Calculate percentages
    high_quality_percentage = round((high_quality_count / total_items) * 100, 2) if total_items > 0 else 0
    low_quality_percentage = round((low_quality_count / total_items) * 100, 2) if total_items > 0 else 0
    
    return {
        "total_items": total_items,
        "high_quality_count": high_quality_count,
        "low_quality_count": low_quality_count,
        "failed_count": failed_count,
        "high_quality_percentage": high_quality_percentage,
        "low_quality_percentage": low_quality_percentage,
        "quality_score_distribution": score_distribution,
        "low_quality_category_distribution": category_distribution,
        "detailed_breakdown": {
            "low_quality_items": [key for key, item in data.items() if item.get("is_high_quality") == False],
            "failed_items": [key for key, item in data.items() if item.get("is_high_quality") is None]
        }
    }

async def process_batch_async_api(batch_items, client, model_name, semaphore):
    """
    Process a batch of items using AsyncOpenAI client
    
    Args:
        batch_items: List of (key, item) tuples to process
        client: AsyncOpenAI client
        model_name: Model name to use
        semaphore: Semaphore to limit concurrency
        
    Returns:
        List of processed items with evaluation results
    """
    async def process_item(key, item):
        question = item["question"]
        answer = item["answer"]
        item_to_filter = f"Question: {question} Answer: {answer}"
        
        try:
            async with semaphore:
                chat_response = await client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": ENG_SYSTEM_PROMPT},
                        {"role": "user", "content": item_to_filter},
                    ],
                    extra_body={"repetition_penalty": 1.05,},
                    temperature=0.7,
                    top_p=0.8,
                )
                
                
                response_content = chat_response.choices[0].message.content
                evaluation_fields = extract_evaluation_fields(response_content)
                
                # Add evaluation fields to item
                item["is_high_quality"] = evaluation_fields["is_high_quality"]
                item["low_quality_category"] = evaluation_fields["low_quality_category"]
                item["quality_score"] = evaluation_fields["quality_score"]
                
                return key, item, True
        except Exception as e:
            item["is_high_quality"] = None
            item["quality_score"] = None
            item["low_quality_category"] = None
            
            return key, item, False
    
    tasks = [process_item(key, item) for key, item in batch_items]
    return await asyncio.gather(*tasks)

async def model_based_filter_async(input_file_path: str, output_file_path: str, 
                                  config: Optional[Dict] = None) -> Tuple[int, int, int, Dict, str]:
    """
    Filter data using model-based evaluation with async API and save results
    
    Args:
        input_file_path: Path to input JSON file
        output_file_path: Path to save filtered results
        config: Configuration dictionary for API settings and test mode
        
    Returns:
        Tuple[int, int, int, Dict, str]: (high_quality_count, low_quality_count, failed_count, detailed_stats, model_name)
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    client = await get_async_client(config)
    model_info = await client.models.list()
    model_name = model_info.data[0].id
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    
    with open(input_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)  # dict

    # Handle test mode
    if config.get("test_mode", False):
        test_limit = config.get("test_limit", 100)
        data_items = list(data.items())[:test_limit]
        data = dict(data_items)

    total_items = len(data)
    high_quality_count = 0
    low_quality_count = 0
    failed_count = 0
    
    # Create batches
    batch_size = config.get("batch_size", 16)
    max_concurrency = config.get("max_concurrency", 8)
    semaphore = asyncio.Semaphore(max_concurrency)
    
    batches = [list(data.items())[i:i+batch_size] for i in range(0, len(data), batch_size)]
    
    # Process batches with progress bar
    progress_bar = tqdm(
        total=total_items,
        desc="Evaluating the quality of data",
        unit="item"
    )
    
    for batch in batches:
        batch_results = await process_batch_async_api(batch, client, model_name, semaphore)
        
        for key, item, success in batch_results:
            if item["is_high_quality"] == True:
                high_quality_count += 1
            elif item["is_high_quality"] == False:
                low_quality_count += 1
            else:
                failed_count += 1
            
            progress_bar.update(1)
            progress_bar.set_postfix({
                'high': high_quality_count,
                'low': low_quality_count, 
                'failed': failed_count
            })

            data[key] = item
    
    progress_bar.close()
    
    # Save modified data
    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    # Calculate detailed statistics
    detailed_stats = calculate_evaluation_statistics(data)
    
    return high_quality_count, low_quality_count, failed_count, detailed_stats, model_name

def process_batch_offline(batch_items, llm, sampling_params):
    """
    Process a batch of items offline
    
    Args:
        batch_items: List of (key, item) tuples to process
        llm: vLLM instance
        sampling_params: Sampling parameters
        
    Returns:
        List of processed items with evaluation results
    """
    conversations = []
    for key, item in batch_items:
        question = item["question"]
        answer = item["answer"]
        item_to_filter = f"Question: {question} Answer: {answer}"
        
        conversation = [
            {"role": "system", "content": ENG_SYSTEM_PROMPT},
            {"role": "user", "content": item_to_filter}
        ]
        conversations.append(conversation)
    
    outputs = llm.chat(conversations, sampling_params)
    
    results = []
    for i, (key, item) in enumerate(batch_items):
        try:
            response_content = outputs[i].outputs[0].text
            evaluation_fields = extract_evaluation_fields(response_content)
            
            # Add evaluation fields to item
            item["is_high_quality"] = evaluation_fields["is_high_quality"]
            item["quality_score"] = evaluation_fields["quality_score"]
            item["low_quality_category"] = evaluation_fields["low_quality_category"]
            
            results.append((key, item, True))
        except Exception as e:
            item["is_high_quality"] = None
            item["quality_score"] = None
            item["low_quality_category"] = None
            
            results.append((key, item, False))
    
    return results

def model_based_filter_offline(input_file_path: str, output_file_path: str, 
                           config: Optional[Dict] = None) -> Tuple[int, int, int, Dict, str]:
    """
    Filter data using model-based evaluation offline and save results
    
    Args:
        input_file_path: Path to input JSON file
        output_file_path: Path to save filtered results
        config: Configuration dictionary for vLLM settings and test mode
        
    Returns:
        Tuple[int, int, int, Dict, str]: (high_quality_count, low_quality_count, failed_count, detailed_stats, model_path)
    """
    
    if config is None:
        config = DEFAULT_CONFIG
    
    model_path = config.get("model_path")
    if model_path is None:
        raise ValueError("Model path must be provided for vLLM inference mode")
    
    # Initialize vLLM
    llm = LLM(model=model_path, tensor_parallel_size=config.get("tensor_parallel_size", 8))
    sampling_params = SamplingParams(temperature=0.7, top_p = 0.8, top_k = 20, max_tokens=16384, repetition_penalty=1.05, seed=42)
    
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        
        with open(input_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)  # dict

        # Handle test mode
        if config.get("test_mode", False):
            test_limit = config.get("test_limit", 100)
            data_items = list(data.items())[:test_limit]
            data = dict(data_items)

        total_items = len(data)
        high_quality_count = 0
        low_quality_count = 0
        failed_count = 0
        
        # Create batches
        batch_size = config.get("batch_size", 16)
        batches = [list(data.items())[i:i+batch_size] for i in range(0, len(data), batch_size)]
        
        # Process batches with progress bar
        progress_bar = tqdm(
            total=total_items,
            desc="Evaluating the quality of data",
            unit="item"
        )
        
        for batch in batches:
            batch_results = process_batch_offline(batch, llm, sampling_params)
            
            for key, item, success in batch_results:
                if item["is_high_quality"] == True:
                    high_quality_count += 1
                elif item["is_high_quality"] == False:
                    low_quality_count += 1
                else:
                    failed_count += 1
                
                progress_bar.update(1)
                progress_bar.set_postfix({
                    'high': high_quality_count,
                    'low': low_quality_count, 
                    'failed': failed_count
                })

                data[key] = item
        
        progress_bar.close()
        
        # Save modified data
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        # Calculate detailed statistics
        detailed_stats = calculate_evaluation_statistics(data)
        
        return high_quality_count, low_quality_count, failed_count, detailed_stats, model_path
        
    finally:
        try:
            del llm
        except:
            pass
        
        try:
            import torch.distributed as dist
            if dist.is_initialized():
                dist.destroy_process_group()
        except Exception as e:
            print(f"Warning: An error occurred while cleaning up the distributed process group: {e}")
        
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        except Exception as e:
            print(f"Warning: An error occurred while cleaning up the CUDA cache: {e}")
        
        try:
            import gc
            gc.collect()
        except Exception as e:
            print(f"警告: 垃圾回收时出现问题: {e}")

def filter(input_file_path: str, output_file_path: str, 
                      config: Optional[Dict] = None) -> Tuple[int, int, int, Dict, str]:
    """
    Filter data using model-based evaluation and save results
    
    Args:
        input_file_path: Path to input JSON file
        output_file_path: Path to save filtered results
        config: Configuration dictionary for API settings and test mode
        
    Returns:
        Tuple[int, int, int, Dict, str]: (high_quality_count, low_quality_count, failed_count, detailed_stats, model_name)
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    inference_mode = config.get("inference_mode", "offline")
    
    if inference_mode == "offline":
        return model_based_filter_offline(input_file_path, output_file_path, config)
    elif inference_mode == "async_api":
        return asyncio.run(model_based_filter_async(input_file_path, output_file_path, config))

if __name__ == "__main__":
    # Configure logging for standalone usage
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    input_file = ""
    output_file = ""
    summary_dir = ""
    
    # Enable test mode for demonstration
    config = DEFAULT_CONFIG.copy()
    config["test_mode"] = True  
    
    logger.info(f"Starting model-based filtering...")
    logger.info(f"Input file: {input_file}")
    logger.info(f"Output file: {output_file}")
    logger.info(f"Test mode: {config['test_mode']}")
    
    high_quality_count, low_quality_count, failed_count, detailed_stats, model_name = filter(input_file, output_file, config)
    
    logger.info(f"Model-based filtering completed:")
    logger.info(f"  High quality items: {high_quality_count}")
    logger.info(f"  Low quality items: {low_quality_count}")
    logger.info(f"  Failed evaluations: {failed_count}")

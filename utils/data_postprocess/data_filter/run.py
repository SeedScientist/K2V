#!/usr/bin/env python3

import os
import sys
import argparse
import traceback
from .data_filter_pipeline import DataFilterPipeline, setup_logging

setup_logging()

parser = argparse.ArgumentParser(description='Run the data filter pipeline.')
parser.add_argument('--input_file', type=str, required=True, help='Path to the input file.')
parser.add_argument('--output_dir', type=str, required=True, help='Directory to save the output.')
parser.add_argument('--inference_mode', choices=['async_api', 'offline'], default='offline',
                    help='Inference mode: async_api, or offline(default)')
parser.add_argument('--test_mode', action='store_true', help='Enable test mode to process only a limited number of data.')
parser.add_argument('--test_limit', type=int, default=10, help='Limit of data to process in test mode.')
parser.add_argument('--openai_api_key', type=str, default='EMPTY', help='OpenAI API key.')
parser.add_argument('--openai_api_base', type=str, default='http://localhost:8000/v1', help='OpenAI API base URL.')
parser.add_argument('--model_path', type=str, help='Local model path for vLLM offline inference mode')
parser.add_argument('--batch_size', type=int, default=100, 
                    help='Batch size for vLLM offline or async API processing')
parser.add_argument('--max_concurrency', type=int, default=100,
                    help='Maximum number of concurrent requests for async API')
parser.add_argument('--tensor_parallel_size', type=int, default=8,
                    help='Tensor parallel size for vLLM offline inference mode')

# Parse arguments
args = parser.parse_args()

# Configuration for the pipeline
config = {
    "openai_api_key": args.openai_api_key,
    "openai_api_base": args.openai_api_base,
    "test_mode": args.test_mode,
    "test_limit": args.test_limit,
    "inference_mode": args.inference_mode,
    "batch_size": args.batch_size,
    "max_concurrency": args.max_concurrency,
    "model_path": args.model_path,
    "tensor_parallel_size": args.tensor_parallel_size
}

# Input and output paths
input_file = args.input_file
output_dir = args.output_dir

# Create pipeline instance
pipeline = DataFilterPipeline(config)

try:
    pipeline.run(input_file, output_dir)
except Exception as e:
    print("Data filtering pipeline fails:")
    traceback.print_exc() 
    sys.exit(1)
    
"""
offline:
python run.py --input_file test_input.json \
              --output_dir output_dir \
              --inference_mode offline 
              --model_path Qwen/Qwen2.5-72B-Instruct \
              --batch_size 1000 \
              --tensor_parallel_size 8

online:
python run.py --input_file test_input.json \
              --output_dir output_dir \
              --inference_mode async_api \
              --openai_api_base http://localhost:8000/v1 \
              --max_concurrency 1000
"""
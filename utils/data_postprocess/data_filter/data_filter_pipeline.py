#!/usr/bin/env python3
"""
Data Filtering Pipeline
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, Optional, Union, Tuple

# Using relative imports for proper package structure

from .regex_based_filter import filter_by_regex
from .model_based_filter import filter as model_based_filter

class DataFilterPipeline:
    """
    Data filtering pipeline that combines regex-based and model-based filtering
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the pipeline with configuration
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.start_time = datetime.now()
        
        # Setup logger for the pipeline
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def create_output_structure(self, base_output_dir: str, timestamp: str = None) -> Dict[str, str]:
        """
        Create output directory structure and return paths
        
        Args:
            base_output_dir: Base directory for all outputs
            timestamp: Optional timestamp string, creates one if not provided
            
        Returns:
            Dictionary containing all output paths
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        # Create main output directory
        output_dir = os.path.join(base_output_dir, f"filtering_results_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Define all output paths
        paths = {
            "output_dir": output_dir,
            "regex_filtered": os.path.join(output_dir, "01_regex_filtered.json"),
            "regex_noisy": os.path.join(output_dir, "01_regex_noisy_data.json"),
            "model_filtered": os.path.join(output_dir, "02_model_filtered.json"),
            "final_high_quality": os.path.join(output_dir, "03_final_high_quality.json"),
            "summary_dir": output_dir,
        }
        
        return paths
        
    def extract_high_quality_data(self, model_filtered_file: str, output_file: str) -> int:
        """
        Extract only high quality data from model filtered results
        
        Args:
            model_filtered_file: Path to model filtered data
            output_file: Path to save high quality data only
            
        Returns:
            Number of high quality items extracted
        """
        self.logger.info("Extracting high quality data...")
        
        with open(model_filtered_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        high_quality_data = {}
        for key, item in data.items():
            if item.get("is_high_quality") == True:
                cleaned_item = item.copy()
                cleaned_item.pop("is_high_quality", None)
                cleaned_item.pop("quality_score", None)
                cleaned_item.pop("low_quality_category", None)   
                high_quality_data[key] = cleaned_item
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(high_quality_data, f, ensure_ascii=False, indent=4)
            
        count = len(high_quality_data)
        self.logger.info(f"Extracted {count} high quality items")
        return count
        
    def save_pipeline_summary(self, paths: Dict[str, str], stats: Dict, input_file_path: str = ""):
        """
        Save comprehensive data filtering pipeline report
        
        Args:
            paths: Dictionary of output paths
            stats: Dictionary of statistics from each step
            input_file_path: Path to the original input file
        """
        # Get model evaluation details if available
        model_filtering_details = stats.get("model_filtering_details", {})
        model_name = stats.get("model_name", "Unknown")
        
        # Create comprehensive report
        report = {
            "pipeline_info": {
                "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_duration": str(datetime.now() - self.start_time),
                "input_file": input_file_path,
                "model_used": model_name,
                "config": self.config
            },
            "filtering_process": {
                "step1_regex_filtering": {
                    "description": "Remove noisy data using regex patterns",
                    "input_items": stats.get("original_count", 0),
                    "output_items": stats.get("regex_remaining", 0),
                    "filtered_items": stats.get("regex_filtered", 0),
                    "filter_rate": f"{stats.get('regex_filtered', 0) / max(stats.get('original_count', 1), 1) * 100:.2f}%"
                },
                "step2_model_filtering": {
                    "description": "Evaluate data quality using LLM",
                    "input_items": stats.get("regex_remaining", 0),
                    "high_quality_items": stats.get("model_high_quality", 0),
                    "low_quality_items": stats.get("model_low_quality", 0),
                    "failed_evaluations": stats.get("model_failed", 0),
                    "success_rate": f"{(stats.get('model_high_quality', 0) + stats.get('model_low_quality', 0)) / max(stats.get('regex_remaining', 1), 1) * 100:.2f}%",
                    "quality_distribution": model_filtering_details.get("quality_score_distribution", {}),
                    "low_quality_categories": model_filtering_details.get("low_quality_category_distribution", {}),
                    "problematic_items": {
                        "low_quality_item_ids": model_filtering_details.get("detailed_breakdown", {}).get("low_quality_items", []),
                        "failed_evaluation_ids": model_filtering_details.get("detailed_breakdown", {}).get("failed_items", [])
                    }
                },
                "step3_final_extraction": {
                    "description": "Extract final high-quality dataset",
                    "high_quality_items": stats.get("final_high_quality", 0)
                }
            },
            "summary": {
                "original_data_count": stats.get("original_count", 0),
                "final_high_quality_count": stats.get("final_high_quality", 0),
                "overall_retention_rate": f"{stats.get('final_high_quality', 0) / max(stats.get('original_count', 1), 1) * 100:.2f}%",
                "total_filtered_count": stats.get("original_count", 0) - stats.get("final_high_quality", 0),
                "filtering_effectiveness": f"{(stats.get('original_count', 0) - stats.get('final_high_quality', 0)) / max(stats.get('original_count', 1), 1) * 100:.2f}%"
            },
            "output_files": {
                "regex_filtered_data": paths["regex_filtered"],
                "regex_noisy_data": paths["regex_noisy"],
                "model_filtered_data": paths["model_filtered"],
                "final_high_quality_data": paths["final_high_quality"]
            }
        }
        
        # Save comprehensive report
        report_path = os.path.join(paths["output_dir"], "data_filtering_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=4)

        
    def run(self, input_file: str, output_dir: str, timestamp: str = None) -> Dict:
        """
        Run the complete filtering pipeline
        
        Args:
            input_file: Path to input JSON file
            output_dir: Base output directory
            timestamp: Optional timestamp for output directory naming
            
        Returns:
            Dictionary containing execution statistics
        """
        self.logger.info("=" * 60)
        self.logger.info("Starting data filtering pipeline")
        self.logger.info("=" * 60)
        self.logger.info(f"Input file: {input_file}")
        self.logger.info(f"Output directory: {output_dir}")
        
        # Create output structure
        paths = self.create_output_structure(output_dir, timestamp)
        self.logger.info(f"Created output directory: {paths['output_dir']}")
        
        # Initialize statistics
        stats = {}
        
        # Get original data count
        with open(input_file, "r", encoding="utf-8") as f:
            original_data = json.load(f)
            stats["original_count"] = len(original_data)
        
        self.logger.info(f"Original data count: {stats['original_count']}")
        
        # Step 1: Regex-based filtering
        self.logger.info("\n" + "Step 1: Regex-based filtering")
        self.logger.info("-" * 40)
        try:
            regex_remaining, regex_filtered = filter_by_regex(
                input_file,
                paths["regex_filtered"],
                paths["regex_noisy"]
            )
            stats["regex_remaining"] = regex_remaining
            stats["regex_filtered"] = regex_filtered
            filter_rate = regex_filtered / stats["original_count"] * 100
            self.logger.info(f"Regex filtering completed:")
            self.logger.info(f"  Remaining: {regex_remaining}")
            self.logger.info(f"  Filtered: {regex_filtered}")
            self.logger.info(f"  Filter rate: {filter_rate:.2f}%")
        except Exception as e:
            self.logger.error(f"Regex filtering failed: {e}")
            raise
            
        # Step 2: Model-based filtering
        self.logger.info("\n" + "Step 2: Model-based filtering")
        self.logger.info("-" * 40)
        test_mode_info = ""
        if self.config.get("test_mode", False):
            test_limit = self.config.get("test_limit", 100)
            test_mode_info = f" (Test mode: {test_limit} items)"
        self.logger.info(f"Processing {regex_remaining} items{test_mode_info}")
        
        try:
            model_high_quality, model_low_quality, model_failed, model_filtering_details, model_name = model_based_filter(
                paths["regex_filtered"],
                paths["model_filtered"],
                self.config
            )
            stats["model_high_quality"] = model_high_quality
            stats["model_low_quality"] = model_low_quality
            stats["model_failed"] = model_failed
            stats["model_filtering_details"] = model_filtering_details
            stats["model_name"] = model_name
            
            total_evaluated = model_high_quality + model_low_quality + model_failed
            self.logger.info(f"Model filtering completed:")
            self.logger.info(f"  High quality: {model_high_quality}")
            self.logger.info(f"  Low quality: {model_low_quality}")
            self.logger.info(f"  Failed: {model_failed}")
            if total_evaluated > 0:
                self.logger.info(f"  Success rate: {(model_high_quality + model_low_quality) / total_evaluated * 100:.2f}%")
        except Exception as e:
            self.logger.error(f"Model filtering failed: {e}")
            raise
            
        # Step 3: Extract final high quality data
        self.logger.info("\n" + "Step 3: Extracting final high quality data")
        self.logger.info("-" * 40)
        try:
            final_high_quality = self.extract_high_quality_data(
                paths["model_filtered"],
                paths["final_high_quality"]
            )
            stats["final_high_quality"] = final_high_quality
        except Exception as e:
            self.logger.error(f"High quality data extraction failed: {e}")
            raise
            
        # Save comprehensive pipeline summary
        self.save_pipeline_summary(paths, stats, input_file)
        
        # Final summary
        self.logger.info("\n" + "=" * 60)
        self.logger.info("Pipeline completed successfully!")
        self.logger.info("=" * 60)
        self.logger.info(f"Final results:")
        self.logger.info(f"  Original data: {stats['original_count']}")
        self.logger.info(f"  Final high quality: {stats['final_high_quality']}")
        retention_rate = stats['final_high_quality'] / stats['original_count'] * 100
        self.logger.info(f"  Overall retention rate: {retention_rate:.2f}%")
        self.logger.info(f"Output directory: {paths['output_dir']}")
        
        return {
            "stats": stats,
            "paths": paths,
            "success": True
        }

def setup_logging(log_file: str = None):
    """
    Setup logging configuration for the pipeline
    
    Args:
        log_file: Optional log file path
    """
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def main():
    """
    Main function for command line usage
    """
    parser = argparse.ArgumentParser(description="Data Filtering Pipeline")
    parser.add_argument("input_file", help="Path to input JSON file")
    parser.add_argument("output_dir", help="Output directory for filtered results")
    parser.add_argument("--timestamp", help="Timestamp for output directory naming")
    parser.add_argument("--test-mode", action="store_true", help="Enable test mode (process only first 100 items)")
    parser.add_argument("--test-limit", type=int, default=100, help="Number of items to process in test mode")
    parser.add_argument("--api-key", default="EMPTY", help="OpenAI API key")
    parser.add_argument("--api-base", default="http://localhost:8000/v1", help="OpenAI API base URL")
    parser.add_argument("--log-file", help="Path to log file")
    # 新增参数
    parser.add_argument("--inference-mode", choices=["api", "async_api", "offline"], default="api",
                        help="Inference mode: api (default), async_api, or offline")
    parser.add_argument("--batch-size", type=int, default=16, 
                        help="Batch size for vLLM or async API processing")
    parser.add_argument("--max-concurrency", type=int, default=8,
                        help="Maximum number of concurrent requests for async API")
    parser.add_argument("--model-path", help="Local model path for vLLM offline inference mode")
    parser.add_argument("--tensor-parallel-size", type=int, default=8,
                        help="Tensor parallel size for vLLM offline inference mode")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_file)
    
    # Create configuration
    config = {
        "openai_api_key": args.api_key,
        "openai_api_base": args.api_base,
        "test_mode": args.test_mode,
        "test_limit": args.test_limit,
        "inference_mode": args.inference_mode,
        "batch_size": args.batch_size,
        "max_concurrency": args.max_concurrency,
        "model_path": args.model_path,
        "tensor_parallel_size": args.tensor_parallel_size
    }
    
    # Create and run pipeline
    pipeline = DataFilterPipeline(config)
    
    try:
        result = pipeline.run(args.input_file, args.output_dir, args.timestamp)
        print(f"\nPipeline completed successfully!")
        print(f"Output directory: {result['paths']['output_dir']}")
        print(f"Final high quality data: {result['stats']['final_high_quality']} items")
        retention_rate = result['stats']['final_high_quality'] / result['stats']['original_count'] * 100
        print(f"Overall retention rate: {retention_rate:.2f}%")
    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 

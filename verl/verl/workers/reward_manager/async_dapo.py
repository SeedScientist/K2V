# Copyright 2024 Bytedance Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
from collections import defaultdict
from functools import partial

import torch

from verl import DataProto
from verl.utils.reward_score import default_compute_score
from verl.workers.reward_manager import register


async def single_compute_score_dapo(evaluation_func, data_source, solution_str, ground_truth, extra_info, semaphore, timeout=300.0):
    """
    Async function to compute score for a single item using semaphore for concurrency control
    """
    try:
        async with semaphore:
            # If evaluation_func is already async, call it directly
            if asyncio.iscoroutinefunction(evaluation_func):
                # Create a task from the coroutine
                future = asyncio.create_task(evaluation_func(
                    data_source=data_source,
                    solution_str=solution_str,
                    ground_truth=ground_truth,
                    extra_info=extra_info,
                ))
                return await asyncio.wait_for(future, timeout=timeout)
            else:
                raise ValueError("The evaluation_func must be async")
    except asyncio.TimeoutError:
        print(f"[Timeout] Task timeout: {solution_str[:80]}")
        return 0.0  # Default value for timed-out rows
    except Exception as e:
        print(f"[Error] Task failed: {e}, solution: {solution_str[:80]}")
        return 0.0  # Default value for failed rows


async def parallel_compute_score_dapo_async(evaluation_func, data_sources, solution_strs, ground_truths, extra_infos, max_concurrency=32, batch_size=16, timeout=300.0):
    """
    Async function to compute scores for multiple items with better concurrency control
    """
    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrency)
    
    # Create batches for better memory management
    total_items = len(data_sources)
    all_results = []
    
    # Process in batches to avoid creating too many tasks at once
    for i in range(0, total_items, batch_size):
        batch_end = min(i + batch_size, total_items)
        
        # Create tasks for current batch
        batch_tasks = [
            single_compute_score_dapo(
                evaluation_func, 
                data_sources[j], 
                solution_strs[j], 
                ground_truths[j], 
                extra_infos[j], 
                semaphore, 
                timeout
            )
            for j in range(i, batch_end)
            ]
        
        try:
            # Execute batch tasks
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            all_results.extend(batch_results)
        except Exception as e:
            print(f"[Exception] Batch processing failed: {e}")
            # Add default values for failed batch
            all_results.extend([0.0] * len(batch_tasks))

    # Process results
    scores = []
    for result, solution_str in zip(all_results, solution_strs):
        if isinstance(result, Exception) or result is None:
            # Handle failed or timed-out tasks
            scores.append(0.0)
        else:
            scores.append(result)
    
    return scores


def run_reward_scoring_dapo(evaluation_func, data_sources, solution_strs, ground_truths, extra_infos, max_concurrency=32, batch_size=16, timeout=300.0):
    """
    Run reward scoring with optimized async processing for I/O bound tasks
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            parallel_compute_score_dapo_async(
                evaluation_func, data_sources, solution_strs, ground_truths, extra_infos, 
                max_concurrency, batch_size, timeout
            )
        )
    finally:
        loop.close()


@register("async_dapo")
class AsyncDAPORewardManager:
    """The async reward manager that combines DAPO features with optimized async computation for I/O bound tasks."""

    def __init__(
        self,
        tokenizer,
        num_examine,
        compute_score=None,
        reward_fn_key="data_source",
        max_resp_len=None,
        overlong_buffer_cfg=None,
        max_concurrency=256,  
        batch_size=256,       
        timeout=500.0,      
    ) -> None:
        self.tokenizer = tokenizer
        self.num_examine = num_examine  # the number of batches of decoded responses to print to the console
        self.compute_score = compute_score or default_compute_score
        self.reward_fn_key = reward_fn_key
        self.overlong_buffer_cfg = overlong_buffer_cfg
        self.max_resp_len = max_resp_len
        self.max_concurrency = max_concurrency  # Max concurrent requests
        self.batch_size = batch_size            # Batch size for processing
        self.timeout = timeout                  # Timeout for each request

        if self.overlong_buffer_cfg is not None:
            assert self.max_resp_len is not None, f"max_resp_len must be provided if {overlong_buffer_cfg=}, but got None"

    def __call__(self, data: DataProto, return_dict: bool = False):
        """Optimized async version of DAPO reward manager for I/O bound tasks"""

        # If there is rm score, we directly return rm score. Otherwise, we compute via rm_score_fn
        if "rm_scores" in data.batch.keys():
            if return_dict:
                return {"reward_tensor": data.batch["rm_scores"]}
            else:
                return data.batch["rm_scores"]

        reward_tensor = torch.zeros_like(data.batch["responses"], dtype=torch.float32)
        reward_extra_info = defaultdict(list)
        already_print_data_sources = {}

        # Prepare data for batch processing
        data_sources = []
        solution_strs = []
        ground_truths = []
        extra_infos = []
        valid_response_lengths = []
        prompt_strs = []

        for i in range(len(data)):
            data_item = data[i]  # DataProtoItem

            prompt_ids = data_item.batch["prompts"]
            prompt_length = prompt_ids.shape[-1]

            valid_prompt_length = data_item.batch["attention_mask"][:prompt_length].sum()
            valid_prompt_ids = prompt_ids[-valid_prompt_length:]

            response_ids = data_item.batch["responses"]
            valid_response_length = data_item.batch["attention_mask"][prompt_length:].sum()
            valid_response_ids = response_ids[:valid_response_length]

            # decode
            prompt_str = self.tokenizer.decode(valid_prompt_ids, skip_special_tokens=True)
            response_str = self.tokenizer.decode(valid_response_ids, skip_special_tokens=True)
            eos_token = self.tokenizer.eos_token
            if response_str.endswith(eos_token):
                response_str = response_str[: -len(eos_token)]

            ground_truth = data_item.non_tensor_batch["reward_model"]["ground_truth"]
            data_source = data_item.non_tensor_batch[self.reward_fn_key]
            extra_info = data_item.non_tensor_batch.get("extra_info", None)

            # Collect data for batch processing
            data_sources.append(data_source)
            solution_strs.append(response_str)
            ground_truths.append(ground_truth)
            extra_infos.append(extra_info)
            valid_response_lengths.append(valid_response_length)
            prompt_strs.append(prompt_str)

        # Batch compute scores using optimized async processing
        try:
            results = run_reward_scoring_dapo(
                self.compute_score,
                data_sources=data_sources,
                solution_strs=solution_strs,
                ground_truths=ground_truths,
                extra_infos=extra_infos,
                max_concurrency=self.max_concurrency,
                batch_size=self.batch_size,
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            print("[Timeout] Global reward scoring timed out. Setting all as 0.")
            results = [0.0 for _ in range(len(data))]
        except Exception as e:
            print(f"[Error] Unexpected error during scoring. Setting all as 0. {e}")
            results = [0.0 for _ in range(len(data))]

        print(f'The length of results is: {len(results)}')

        # Process results and apply DAPO-specific logic
        for i, (result, valid_response_length, prompt_str, solution_str, ground_truth, data_source) in enumerate(
            zip(results, valid_response_lengths, prompt_strs, solution_strs, ground_truths, data_sources)
        ):
            score: float
            if isinstance(result, dict):
                score = result["score"]
                # Store the information including original reward
                for key, value in result.items():
                    reward_extra_info[key].append(value)
            else:
                score = result

            reward = score

            # Apply overlong buffer logic if configured
            if self.overlong_buffer_cfg is not None and self.overlong_buffer_cfg.enable:
                overlong_buffer_len = self.overlong_buffer_cfg.len
                expected_len = self.max_resp_len - overlong_buffer_len
                exceed_len = valid_response_length - expected_len
                overlong_penalty_factor = self.overlong_buffer_cfg.penalty_factor
                overlong_reward = min(-exceed_len / overlong_buffer_len * overlong_penalty_factor, 0)
                reward += overlong_reward
                if self.overlong_buffer_cfg.log:
                    reward_extra_info["overlong_reward"].append(overlong_reward)
                    reward_extra_info["overlong"].append(overlong_reward < 0)

            reward_tensor[i, valid_response_length - 1] = reward

            # Print examination results
            if data_source not in already_print_data_sources:
                already_print_data_sources[data_source] = 0

            if already_print_data_sources[data_source] < self.num_examine:
                already_print_data_sources[data_source] += 1
                print("[prompt]", prompt_str)
                print("[response]", solution_str)
                print("[ground_truth]", ground_truth)
                if isinstance(result, dict):
                    for key, value in result.items():
                        print(f"[{key}]", value)
                else:
                    print("[score]", score)

        if return_dict:
            return {
                "reward_tensor": reward_tensor,
                "reward_extra_info": reward_extra_info,
            }
        else:
            return reward_tensor
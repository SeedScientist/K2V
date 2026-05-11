import torch
from collections import defaultdict

from verl import DataProto
from verl.workers.reward_manager import register

@register("seedbench")
class SeedBenchValManager:
    def __init__(
        self,
        tokenizer,
        num_examine,
        compute_score=None,
        reward_fn_key="data_source",
        max_resp_len=None,
        overlong_buffer_cfg=None,
    ) -> None:
        if compute_score is None:
            raise ValueError("val compute_score must be provided")

        self.tokenizer = tokenizer
        self.num_examine = num_examine  # the number of batches of decoded responses to print to the console
        self.compute_score = compute_score 
        self.reward_fn_key = reward_fn_key
        self.overlong_buffer_cfg = overlong_buffer_cfg
        self.max_resp_len = max_resp_len

    def __call__(self, data: DataProto, return_dict=False):
        val_extra_info = defaultdict(list)
        val_score = []

        for i in range(len(data)):
            data_item = data[i]  # DataProtoItem

            prompt_ids = data_item.batch["prompts"]

            prompt_length = prompt_ids.shape[-1]

            # valid_prompt_length = data_item.batch["attention_mask"][:prompt_length].sum()
            # valid_prompt_ids = prompt_ids[-valid_prompt_length:]

            response_ids = data_item.batch["responses"]
            valid_response_length = data_item.batch["attention_mask"][prompt_length:].sum()
            valid_response_ids = response_ids[:valid_response_length]

            # decode
            # prompt_str = self.tokenizer.decode(valid_prompt_ids, skip_special_tokens=True)
            response_str = self.tokenizer.decode(valid_response_ids, skip_special_tokens=True)

            ground_truth = data_item.non_tensor_batch["reward_model"]["ground_truth"]
            data_source = data_item.non_tensor_batch[self.reward_fn_key]
            extra_info = data_item.non_tensor_batch.get("extra_info", None)

            question = extra_info["question"]   # question在extra_info中
            question_type = extra_info["question_type"]

            result = self.compute_score(
                data_source=data_source,
                question=question,
                solution_str=response_str,
                ground_truth=ground_truth,
                extra_info=extra_info,
            )

            if isinstance(result, dict):
                val_score.append({'score': result["score"], 'question': question, 'question_type': question_type})
                for key, value in result.items():
                    val_extra_info[key].append(value)
            else:
                val_score.append({'score': result, 'question': question, 'question_type': question_type})

        if return_dict:
            return {
                "val_score": val_score,
                "val_extra_info": val_extra_info,
            }
        else:
            return val_score
"""
Convert the data to parquet format that verl can use
"""

import argparse
import os
import re
import json
import datasets

def convert_checklist_data_to_parquet(question, ground_truth, index, data_source, hash_id, checklist):
    instruction = (
        "Answer the following question. "
        "You must first think about the reasoning process in the mind and then provide the user with the answer. The reasoning process and answer are enclosed within <think> </think> and <answer> </answer> tags, respectively, i.e., <think> reasoning process here </think> <answer> answer here </answer>.\n"
        "The question is as follows:\n"
    )
    prompt = instruction + question
    checklist_list = json.loads(checklist)
    parquet_data = {
        "data_source": data_source,
        "prompt": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "ability": "agriculture",
        "reward_model": {"style": "rule", "ground_truth": ground_truth},
        "extra_info": {
            "split": "train",
            "index": index,
            "data_hash": hash_id,
            "data_type": "checklist_data",
            "checklist": checklist,
            "question": question
        },
    }   
    return parquet_data

def convert_data_to_parquet(json_file_path, parquet_file_path):
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f) # dict

    all_parquet_data = []
    data_source = "K2V/checklist"
    for index, (hash_id, single_data) in enumerate(data.items()):
        question = single_data["question"]
        ground_truth = single_data["answer"]
        checklist = single_data["checklist"]
        parquet_data = convert_checklist_data_to_parquet(question, ground_truth, index, data_source, hash_id, checklist)
        all_parquet_data.append(parquet_data)

    dataset = datasets.Dataset.from_list(all_parquet_data)
    dataset.to_parquet(parquet_file_path)
    return dataset

if __name__ == "__main__":
    json_file_path = ''
    parquet_file_path = ''
    convert_data_to_parquet(json_file_path, parquet_file_path)


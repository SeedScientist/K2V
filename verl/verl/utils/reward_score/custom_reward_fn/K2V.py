import re
import asyncio
from openai import AsyncOpenAI

def extract_answer_without_box(text: str) -> str:
    answer = text.split("<answer>")[-1]
    answer = answer.split("</answer>")[0]
    return answer.strip()

def extract_think(text: str) -> str:
    think = text.split("<think>")[-1]
    think = think.split("</think>")[0]
    return think.strip()

def hard_answer_match(prediction: str, ground_truth: str) -> bool:
    if prediction == ground_truth:
        return True
    return False

def fill_blank_answer_reward_fn(solution_str: str, ground_truth: str) -> dict:
    prediction = extract_answer_without_box(solution_str)
    hard_match = hard_answer_match(prediction, ground_truth)
    
    rewards = {
        "hard_answer_match_reward": 6.0 if hard_match else 0.0,
    }
    return rewards

async def checklist_reward_fn(solution_str: str, checklist: list, question: str, ground_truth: str, checklist_judge_model_url: str) -> float:
    async with AsyncOpenAI(
        api_key="EMPTY",
        base_url=checklist_judge_model_url,
    ) as client:
        model_info = await client.models.list()
        model_name = model_info.data[0].id

        think = extract_think(solution_str)
        system_prompt = (
            "You are an impartial and meticulous AI examiner, specializing in agriculture and biology. "
            "Your task is to evaluate a student's [Reasoning Process] for a given [Question-Answer Pair] against a specific, detailed [criterion]. "
            "The [Question-Answer Pair] is a fill-in-the-blank question in the field of agriculture or biology, with '{ }' indicating the content to be filled in. A fill-in-the-blank question may contain multiple '{ }', and the content to be filled in for each '{ }' is the same. "
            "Your judgment must be strict, objective, and based solely on the provided information.\n"
            'NOTE: Your output can only be "yes" or "no"'
        )
        
        async def evaluate_by_single_criterion(criterion: str) -> bool:
            user_prompt = (
                f"[Question-Answer Pair]\nquestion: {question}\nanswer: {ground_truth}\n"
                f"[criterion]\n{criterion}\n"
                f"[Reasoning Process]\n{think}"
            )
            message = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            
            try:
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=message,
                    extra_body={"repetition_penalty": 1.05,},
                    temperature=0.7,
                    top_p=0.8,
                    max_tokens=8,
                    timeout=150.0,
                )
                response_text = response.choices[0].message.content.strip().lower()
                return response_text == "yes"
            except Exception as e:
                print(f"Error evaluating a single criterion: {e}")
                return False
        
        tasks = [evaluate_by_single_criterion(criterion) for criterion in checklist]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        satisfied_count = sum(1 for result in results if result is True)
        total_checklist = len(checklist)
        
        if total_checklist == 0:
            return 0.0
        
        checklist_score = (satisfied_count / total_checklist) 
        return checklist_score

async def accuracy_reward_fn(solution_str: str, ground_truth: str, 
                             enable_checklist_reward: bool,
                             checklist_judge_model_url: str,
                             extra_info: dict) -> dict:
    answer_rewards = fill_blank_answer_reward_fn(solution_str, ground_truth)

    hard_reward = answer_rewards["hard_answer_match_reward"]    # The max hard_reward is 6.0
    result = {
        "hard_answer_match_reward": hard_reward,
    }

    if enable_checklist_reward:
        checklist = extra_info["checklist"]
        question = extra_info["question"]
        if hard_reward > 0.0:
            checklist_reward = await checklist_reward_fn(solution_str, checklist, question, ground_truth, checklist_judge_model_url) # The max checklist_reward is 1.0
            result["checklist_reward"] = checklist_reward 
            result["total_reward"] = result["checklist_reward"] + result["hard_answer_match_reward"] 
        else:
            result["checklist_reward"] = 0.0
            result["total_reward"] = result["checklist_reward"] + result["hard_answer_match_reward"] 
    else:
        result["checklist_reward"] = None
        result["total_reward"] = result["hard_answer_match_reward"] 
    return result

def count_format_reward_fn(solution_str) -> float:
    count = 0.0
    if solution_str.count("<think>") == 1:
        count += 0.125
    if solution_str.count("</think>") == 1:
        count += 0.125
    if solution_str.count("<answer>") == 1:
        count += 0.125
        count -= len(solution_str.split("</answer>")[-1])*0.001
    if solution_str.count("</answer>") == 1:
        count += 0.125
        count -= (len(solution_str.split("</answer>")[-1]) - 1)*0.001
    return count

def format_reward_fn(solution_str) -> float:
    pattern = r"<think>.*?</think>\s*<answer>.*?</answer>"
    match = re.match(pattern, solution_str, flags=re.DOTALL)
    format_reward = 0.25 + count_format_reward_fn(solution_str) if match else 0.0
    return format_reward

async def compute_reward_fn(data_source, solution_str, ground_truth, extra_info,
                      enable_checklist_reward: bool, checklist_judge_model_url: str) -> dict:
    acc_result = await accuracy_reward_fn(solution_str, ground_truth, 
                                    enable_checklist_reward, checklist_judge_model_url,
                                    extra_info)
    format_reward = format_reward_fn(solution_str)
    
    result = {
        "score": acc_result["total_reward"] + format_reward,
        "accuracy_reward": acc_result["total_reward"],   
        "format_reward": format_reward,
        "hard_answer_match_reward": acc_result["hard_answer_match_reward"]
    }
    
    if enable_checklist_reward and acc_result["checklist_reward"] is not None:
        result["checklist_reward"] = acc_result["checklist_reward"]
    
    return result
    

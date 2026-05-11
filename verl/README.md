## What is this module
This module contains the framework used by K2V to train models. We developed this framework based on **[verl](https://github.com/volcengine/verl)**.

## Installation
We recommend to use a fresh new conda environment to install verl and its dependencies.
  ```bash
  conda create --name verl python=3.11 -y
  conda activate verl
  ```

Install the necessary dependencies.
  ```bash
  git clone https://github.com/superfarther/verl.git
  pip install -r requirements_K2V.txt
  ```

Install the verl from source.
  ```bash
  pip install --no-deps -e .
  ```

K2V uses **[vLLM](https://github.com/vllm-project/vllm)** as the inference framework. Notice that vLLM often strictly limit your pytorch version and will directly override your installed pytorch. As a countermeasure, it is recommended to install vLLM first with the pytorch they needed. Overall, we need to ensure that the versions of the following dependencies are consistent with those specified in `requirements_K2V.txt`.
- torch and torch series
- vLLM
- pyarrow
- tensordict
- nvidia-cudnn-cu12

## RL training
1. Deploy a judge model using vLLM to verify the model's reasoning process. For example, we can use Qwen2.5-7B-Instruct as the judge model.
    ```bash
    CUDA_VISIBLE_DEVICES=4,5,6,7 vllm serve Qwen/Qwen2.5-7B-Instruct--tensor-parallel-size 4 --gpu_memory_utilization 0.7 
    ```

2. We provide example data, which is stored in the `K2V-example/data`. Additionally, a example configuration file is available at `K2V-example/config.sh`. Before starting the training, you need to fill in the relevant paths in the configuration file.
   - **train_files:** Path of training data
   - **val_files:** Path of validation data
   - **rollout_data_dir:** Rollout data generated during training will be saved to this directory.
   - **validation_data_dir:** Validation result will be saved to this directory.
   - **default_local_dir:** Checkpoint will be saved to this directory.
   - **log_file:** Path of log file
   - **checklist_judge_model_url:** Service endpoint for the judge model deployed with vLLM.

3. Start training
    ```bash
    bash K2V-example/config.sh
    ```

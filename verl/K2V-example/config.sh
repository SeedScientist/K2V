
set -xeuo pipefail

version="yyyymmdd"
export SWANLAB_MODE=local
export SWANLAB_LOG_DIR="K2V-example/${version}/swanlab"
export HYDRA_FULL_ERROR=1

# path
train_files=K2V-example/data/example_training_data.parquet
val_files=K2V-example/data/example_val_data.parquet
rollout_data_dir=K2V-example/${version}/rollout_data
validation_data_dir=K2V-example/${version}/validation_data
default_local_dir=K2V-example/${version}/record
log_file=K2V-example/${version}/record/${version}.log
checklist_judge_model_url=

# sequence length
max_prompt_length=$((1024))
max_response_length=$((1024*4))
overlong_buffer_length=$((512))

# max token length for rollout
actor_ppo_max_token_len=$((max_prompt_length + max_response_length))
infer_ppo_max_token_len=$((max_prompt_length + max_response_length))

# batch size
train_batch_size=$((64))
train_prompt_mini_bsz=$((32))

# vLLM config
# max_num_batched_tokens=$((max_prompt_length + max_response_length))
max_num_batched_tokens=$((8192+1024))

# Dynamic Sampling (with Group Filtering)
enable_filter_groups=True
filter_groups_metric=seq_reward
gen_prompt_bsz=$((train_batch_size * 3))
max_num_gen_batches=-1

# KL
use_kl_in_reward=False
kl_coef=0.0
use_kl_loss=False
kl_loss_coef=0.0

# other
n_gpus_per_node=$((8))
tensor_parallel_size=$((1))
offload=True

python3 -m recipe.dapo.main_dapo \
    algorithm.adv_estimator=grpo \
    algorithm.use_kl_in_reward=${use_kl_in_reward} \
    algorithm.filter_groups.enable=${enable_filter_groups} \
    algorithm.filter_groups.max_num_gen_batches=${max_num_gen_batches} \
    algorithm.filter_groups.metric=${filter_groups_metric} \
    algorithm.kl_ctrl.kl_coef=${kl_coef} \
    \
    data.train_files=${train_files} \
    data.val_files=${val_files} \
    data.train_batch_size=${train_batch_size} \
    data.max_prompt_length=${max_prompt_length} \
    data.max_response_length=${max_response_length} \
    data.gen_batch_size=${gen_prompt_bsz} \
    data.filter_overlong_prompts=True \
    data.truncation='error' \
    \
    actor_rollout_ref.rollout.disable_log_stats=False \
    actor_rollout_ref.model.path= \
    actor_rollout_ref.actor.optim.lr=1e-7 \
    actor_rollout_ref.model.use_remove_padding=True \
    actor_rollout_ref.actor.ppo_mini_batch_size=${train_prompt_mini_bsz} \
    actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=16 \
    actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu=16 \
    actor_rollout_ref.ref.log_prob_micro_batch_size_per_gpu=16 \
    actor_rollout_ref.actor.use_kl_loss=${use_kl_loss} \
    actor_rollout_ref.actor.kl_loss_coef=${kl_loss_coef} \
    actor_rollout_ref.actor.entropy_coeff=0 \
    actor_rollout_ref.model.enable_gradient_checkpointing=True \
    actor_rollout_ref.actor.fsdp_config.param_offload=${offload} \
    actor_rollout_ref.actor.fsdp_config.optimizer_offload=${offload} \
    actor_rollout_ref.rollout.name=vllm \
    actor_rollout_ref.rollout.tensor_model_parallel_size=${tensor_parallel_size} \
    actor_rollout_ref.rollout.gpu_memory_utilization=0.8 \
    actor_rollout_ref.rollout.n=8 \
    actor_rollout_ref.ref.fsdp_config.param_offload=${offload} \
    actor_rollout_ref.actor.clip_ratio_low=0.2 \
    actor_rollout_ref.actor.clip_ratio_high=0.28 \
    actor_rollout_ref.actor.ppo_max_token_len_per_gpu=${actor_ppo_max_token_len} \
    actor_rollout_ref.ref.log_prob_max_token_len_per_gpu=${infer_ppo_max_token_len} \
    actor_rollout_ref.rollout.log_prob_max_token_len_per_gpu=${infer_ppo_max_token_len} \
    actor_rollout_ref.rollout.max_num_batched_tokens=${max_num_batched_tokens} \
    \
    custom_reward_function.path=verl/utils/reward_score/custom_reward_fn/K2V.py \
    custom_reward_function.name=compute_reward_fn \
    +custom_reward_function.reward_kwargs.enable_checklist_reward=True \
    +custom_reward_function.reward_kwargs.checklist_judge_model_url=${checklist_judge_model_url} \
    \
    custom_val_reward_function.enable=False \
    \
    reward_model.reward_manager=async_dapo \
    reward_model.overlong_buffer.enable=True \
    reward_model.overlong_buffer.len=${overlong_buffer_length} \
    reward_model.overlong_buffer.penalty_factor=1.0 \
    \
    trainer.critic_warmup=0 \
    trainer.logger=['console','swanlab'] \
    trainer.project_name=${version} \
    trainer.experiment_name=${version} \
    trainer.n_gpus_per_node=${n_gpus_per_node} \
    trainer.nnodes=1 \
    trainer.val_before_train=False \
    trainer.log_val_generations=0 \
    trainer.save_freq=20 \
    trainer.test_freq=-1 \
    trainer.rollout_data_dir=${rollout_data_dir} \
    trainer.validation_data_dir=${validation_data_dir} \
    trainer.default_local_dir=${default_local_dir} \
    trainer.total_epochs=6 2>&1 | tee ${log_file} $@
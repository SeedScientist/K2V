## What is this module
This module contains the utils used by K2V to synthesize checklist.

## How to use
1. After synthesizing fill-blank style QA pairs using **[graphgen-mask](https://github.com/superfarther/graphgen-mask.git)**, we need to synthesize a question-specific checklist for each QA pair.
    ```bash
    bash data_postprocess/run.sh \
      --input_file  \
      --output_dir  \
      --model_path Qwen/Qwen2.5-72B-Instruct \
      --inference_mode offline \
      --batch_size 2000 \
      --tensor_parallel_size 8 \
      --domain EN_AGRI \
    ```

2. `data_postprocess/run.sh` will automatically execute a data filtering pipeline. If you want to retain the all data, you can directly run the following script.
    ```bash
    python data_postprocess/synthesize_checklist/synthesize_checklist.py
    ```

3. Convert the data from JSON format to Parquet format.
    ```bash
    python verl/convert_json_to_parquet.py
    ```

4. **[verl](https://github.com/superfarther/verl)** needs a validation set to be specified to start training. Here, we choose to randomly sample from the training set as the validation set.
    ```bash
    python verl/get_val_dataset.py
    ```
 
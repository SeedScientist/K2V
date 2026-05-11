## What is this module
This module contains the framework used by K2V to synthesize fill-blank style QA pairs. We developed this framework based on **[GraphGen](https://github.com/open-sciencelab/GraphGen)**.

## Installation
We recommend to begin with a fresh new conda environment.
  ```bash
  conda create --name verl python=3.10 -y
  conda activate graphgen-mask
  ```

Install the necessary dependencies.
  ```bash
  git clone https://github.com/superfarther/graphgen-mask.git
  pip install -r requirements_K2V.txt
  ```

**Note:** This module is significantly outdated compared to the official [GraphGen](https://github.com/open-sciencelab/GraphGen). To use the latest code for synthesizing QA pairs, you can visit the official GraphGen repository and navigate to the examples/generate/generate_masked_fill_in_blank_qa.

## Synthesize QA Pairs
1. In order to construct a KG from corpus, K2V deploy a LLM using **[vLLM](https://github.com/vllm-project/vllm)** to perform Named Entity Recognition (NER) and Relation Extraction (RE).
   ```bash
   vllm serve Qwen/Qwen2.5-72B-Instruct --max_model_len 32768
   ```

2. Configure the environment
   - Create an `.env` file in the root directory
      ```bash
      cp .env.example .env
      ```
   - fill in the necessary key in the `.env`
      - **SYNTHESIZER_MODEL:** Local path of LLM deployed with vLLM
      - **SYNTHESIZER_BASE_URL:** Service endpoint for the LLM deployed with vLLM.
      - **SYNTHESIZER_API_KEY:** (optional) API key.

3. We provide example corpus, which is stored in the `K2V-example/data/example_corpus.json`. Additionally, a example configuration file is available at `K2V-example/config.yaml`. 

4. Run the generation script
    ```bash
    bash K2V-example/run.sh
    ```




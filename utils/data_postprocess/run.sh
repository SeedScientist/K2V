#!/bin/bash

set -e  # Exit on any error

# Default values
INFERENCE_MODE="offline"
TEST_MODE=false
TEST_LIMIT=100
BATCH_SIZE=16
MAX_CONCURRENCY=8
TENSOR_PARALLEL_SIZE=8
OPENAI_API_KEY="EMPTY"
OPENAI_API_BASE="http://localhost:8000/v1"

# Function to show usage
show_usage() {
    echo "Usage: $0 --input_file INPUT_FILE --output_dir OUTPUT_DIR --model_path MODEL_PATH --domain DOMAIN [OPTIONS]"
    echo ""
    echo "Required arguments:"
    echo "  --input_file INPUT_FILE        Path to input JSON file"
    echo "  --output_dir OUTPUT_DIR        Output directory for all results"
    echo "  --model_path MODEL_PATH        Local model path for vLLM"
    echo "  --domain DOMAIN                Domain for checklist: EN_AGRI, EN_MEDICINE, EN_LAW"
    echo ""
    echo "Optional arguments:"
    echo "  --inference_mode MODE          Inference mode: async_api, offline (default: offline)"
    echo "  --test_mode                    Enable test mode"
    echo "  --test_limit N                 Test mode limit (default: 100)"
    echo "  --batch_size N                 Batch size (default: 16)"
    echo "  --max_concurrency N            Max concurrency for async API (default: 8)"
    echo "  --tensor_parallel_size N       Tensor parallel size (default: 8)"
    echo "  --openai_api_key KEY           OpenAI API key (default: EMPTY)"
    echo "  --openai_api_base URL          OpenAI API base URL (default: http://localhost:8000/v1)"
    echo "  --help                         Show this help message"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --input_file)
            INPUT_FILE="$2"
            shift 2
            ;;
        --output_dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --model_path)
            MODEL_PATH="$2"
            shift 2
            ;;
        --inference_mode)
            INFERENCE_MODE="$2"
            shift 2
            ;;
        --test_mode)
            TEST_MODE=true
            shift
            ;;
        --test_limit)
            TEST_LIMIT="$2"
            shift 2
            ;;
        --batch_size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --max_concurrency)
            MAX_CONCURRENCY="$2"
            shift 2
            ;;
        --tensor_parallel_size)
            TENSOR_PARALLEL_SIZE="$2"
            shift 2
            ;;
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --openai_api_key)
            OPENAI_API_KEY="$2"
            shift 2
            ;;
        --openai_api_base)
            OPENAI_API_BASE="$2"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check required arguments
if [[ -z "$INPUT_FILE" || -z "$OUTPUT_DIR" || -z "$MODEL_PATH" || -z "$DOMAIN" ]]; then
    echo "Error: Missing required arguments"
    if [[ -z "$DOMAIN" ]]; then
        echo "Domain parameter is required. Please specify --domain with one of: EN_AGRI, EN_MEDICINE, EN_LAW"
    fi
    show_usage
    exit 1
fi

# Check if input file exists
if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Error: Input file does not exist: $INPUT_FILE"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================"
echo "Complete Data Processing Pipeline"
echo "========================================"
echo "Input file: $INPUT_FILE"
echo "Output directory: $OUTPUT_DIR"
echo "Model path: $MODEL_PATH"
echo "Inference mode: $INFERENCE_MODE"
echo "Test mode: $TEST_MODE"
if [[ "$TEST_MODE" == true ]]; then
    echo "Test limit: $TEST_LIMIT"
fi
echo "Domain: $DOMAIN"
echo ""

# Step 1: Run data filtering pipeline
echo "Step 1: Running data filtering pipeline..."
echo "----------------------------------------"

# Go to graphgen directory to run as module with proper package hierarchy
cd "$(dirname "$SCRIPT_DIR")"

FILTER_ARGS="--input_file $INPUT_FILE --output_dir $OUTPUT_DIR --inference_mode $INFERENCE_MODE"
FILTER_ARGS="$FILTER_ARGS --model_path $MODEL_PATH --batch_size $BATCH_SIZE"
FILTER_ARGS="$FILTER_ARGS --max_concurrency $MAX_CONCURRENCY --tensor_parallel_size $TENSOR_PARALLEL_SIZE"
FILTER_ARGS="$FILTER_ARGS --openai_api_key $OPENAI_API_KEY --openai_api_base $OPENAI_API_BASE"

if [[ "$TEST_MODE" == true ]]; then
    FILTER_ARGS="$FILTER_ARGS --test_mode --test_limit $TEST_LIMIT"
fi

python -m data_postprocess.data_filter.run $FILTER_ARGS

if [[ $? -ne 0 ]]; then
    echo "Error: Data filtering pipeline failed"
    exit 1
fi

# Find the latest output directory (filtering_results_*)
FILTER_OUTPUT_DIR=$(find "$OUTPUT_DIR" -name "filtering_results_*" -type d | sort | tail -1)
if [[ -z "$FILTER_OUTPUT_DIR" ]]; then
    echo "Error: Could not find filtering results directory"
    exit 1
fi

HIGH_QUALITY_FILE="$FILTER_OUTPUT_DIR/03_final_high_quality.json"
if [[ ! -f "$HIGH_QUALITY_FILE" ]]; then
    echo "Error: High quality data file not found: $HIGH_QUALITY_FILE"
    exit 1
fi

echo "Data filtering completed successfully!"
echo "High quality data file: $HIGH_QUALITY_FILE"
echo ""

# Step 2: Run checklist synthesis
echo "Step 2: Running checklist synthesis..."
echo "------------------------------------"

# Stay in graphgen directory for consistent package structure
# cd "$SCRIPT_DIR"

# Generate output filename for checklist
BASENAME=$(basename "$INPUT_FILE" .json)
CHECKLIST_OUTPUT_FILE="$FILTER_OUTPUT_DIR/${BASENAME}_with_checklist.json"

# Run checklist synthesis with command line arguments
CHECKLIST_ARGS="--input_file $HIGH_QUALITY_FILE --output_file $CHECKLIST_OUTPUT_FILE --model_path $MODEL_PATH --domain $DOMAIN"
CHECKLIST_ARGS="$CHECKLIST_ARGS --batch_size $BATCH_SIZE --tensor_parallel_size $TENSOR_PARALLEL_SIZE"

if [[ "$TEST_MODE" == true ]]; then
    CHECKLIST_ARGS="$CHECKLIST_ARGS --test_mode --test_limit $TEST_LIMIT"
fi

python -m data_postprocess.synthesize_checklist.synthesize_checklist $CHECKLIST_ARGS

if [[ $? -ne 0 ]]; then
    echo "Error: Checklist synthesis failed"
    exit 1
fi

echo ""
echo "========================================"
echo "Pipeline completed successfully!"
echo "========================================"
echo "Final output with checklist: $CHECKLIST_OUTPUT_FILE"
echo "All results are in: $FILTER_OUTPUT_DIR"
echo ""

# ./run.sh \
#   --input_file  \
#   --output_dir  \
#   --model_path Qwen/Qwen2_5-72B-instruct \
#   --inference_mode offline \
#   --batch_size 2000 \
#   --tensor_parallel_size 8 \
#   --domain EN_AGRI \

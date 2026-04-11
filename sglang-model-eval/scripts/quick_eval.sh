#!/bin/bash
# Quick single benchmark test - assumes server is already running
# Usage: ./quick_eval.sh [EVAL_NAME] [PORT] [NUM_EXAMPLES] [MAX_TOKENS]

EVAL_NAME="${1:-gpqa}"
PORT="${2:-30000}"
NUM_EXAMPLES="${3:-198}"
MAX_TOKENS="${4:-32768}"

echo "Running ${EVAL_NAME} benchmark on port ${PORT}..."

case "${EVAL_NAME}" in
    gpqa)
        python -m sglang.test.run_eval \
            --eval-name gpqa \
            --port "${PORT}" \
            --num-examples "${NUM_EXAMPLES}" \
            --max-tokens "${MAX_TOKENS}"
        ;;
    mmlu)
        python -m sglang.test.run_eval \
            --eval-name mmlu \
            --port "${PORT}" \
            --num-examples "${NUM_EXAMPLES}" \
            --max-tokens "${MAX_TOKENS}"
        ;;
    humaneval)
        pip install human_eval -q
        python -m sglang.test.run_eval \
            --eval-name humaneval \
            --num-examples "${NUM_EXAMPLES}" \
            --port "${PORT}"
        ;;
    gsm8k)
        python -m sglang.test.few_shot_gsm8k \
            --host 127.0.0.1 \
            --port "${PORT}" \
            --num-questions "${NUM_EXAMPLES}" \
            --num-shots 5
        ;;
    latency)
        python -m sglang.bench_serving \
            --backend sglang \
            --port "${PORT}" \
            --dataset-name random \
            --num-prompts 10 \
            --max-concurrency 1
        ;;
    throughput)
        python -m sglang.bench_serving \
            --backend sglang \
            --port "${PORT}" \
            --dataset-name random \
            --num-prompts 1000 \
            --max-concurrency 100
        ;;
    *)
        echo "Unknown benchmark: ${EVAL_NAME}"
        echo "Supported: gpqa, mmlu, humaneval, gsm8k, latency, throughput"
        exit 1
        ;;
esac

# SGLang Benchmark Reference

## Accuracy Benchmarks

### GPQA (Graduate-Level Google-Proof Q&A)

**Purpose**: Tests advanced reasoning and domain expertise

- **Type**: Multiple-choice questions requiring expert-level knowledge
- **Domains**: Biology, Physics, Chemistry
- **Default Examples**: 198
- **Recommended Max Tokens**: 120000
- **Repeat**: 8 (for statistical significance)

```bash
python -m sglang.test.run_eval \
  --eval-name gpqa \
  --port 30000 \
  --num-examples 198 \
  --max-tokens 120000 \
  --repeat 8
```

### MMLU (Massive Multitask Language Understanding)

**Purpose**: Tests broad knowledge across 57 subjects

- **Type**: Multiple-choice questions
- **Domains**: STEM, humanities, social sciences, other
- **Default Examples**: 1000 (full: ~14,000)
- **Recommended Max Tokens**: 8192

```bash
python -m sglang.test.run_eval \
  --eval-name mmlu \
  --port 30000 \
  --num-examples 1000 \
  --max-tokens 8192
```

### GSM8K (Grade School Math 8K)

**Purpose**: Tests multi-step mathematical reasoning

- **Type**: Math word problems
- **Default Questions**: 200 (full: 1,319 test)
- **Few-shot**: 5 examples

```bash
python -m sglang.test.few_shot_gsm8k \
  --host 127.0.0.1 \
  --port 30000 \
  --num-questions 200 \
  --num-shots 5
```

### HumanEval

**Purpose**: Tests code generation ability

- **Type**: Python function completion
- **Default Examples**: 10 (full: 164)
- **Requires**: `pip install human_eval`

```bash
pip install human_eval

python -m sglang.test.run_eval \
  --eval-name humaneval \
  --num-examples 10 \
  --port 30000
```

### HellaSwag

**Purpose**: Tests common sense reasoning

- **Type**: Sentence completion
- **Default Questions**: 200
- **Few-shot**: 20 examples

```bash
python benchmark/hellaswag/bench_sglang.py \
  --host 127.0.0.1 \
  --port 30000 \
  --num-questions 200 \
  --num-shots 20
```

## Performance Benchmarks

### Latency Benchmark

Measures Time To First Token (TTFT) - critical for interactive applications.

```bash
python -m sglang.bench_serving \
  --backend sglang \
  --port 30000 \
  --dataset-name random \
  --num-prompts 10 \
  --max-concurrency 1
```

**Metrics**:
- TTFT (Time To First Token)
- End-to-end latency

### Throughput Benchmark

Measures maximum tokens per second under load.

```bash
python -m sglang.bench_serving \
  --backend sglang \
  --port 30000 \
  --dataset-name random \
  --num-prompts 1000 \
  --max-concurrency 100
```

**Metrics**:
- Tokens/second
- Requests/second

### Concurrency Levels

| Level | Prompts | Concurrency | Use Case |
|-------|---------|-------------|----------|
| Low | 10 | 1 | Single user latency |
| Medium | 80 | 16 | Typical production |
| High | 500 | 100 | Peak load testing |

### Single Batch Performance

Offline batch processing benchmark:

```bash
python -m sglang.bench_one_batch_server \
  --model <MODEL_PATH> \
  --batch-size 8 \
  --input-len 1024 \
  --output-len 1024
```

## VLM Benchmarks

### MMMU (Multimodal Multi-discipline Understanding)

For vision-language models:

```bash
python benchmark/mmmu/bench_sglang.py \
  --port 30000 \
  --concurrency 64
```

Optional max tokens:
```bash
python benchmark/mmmu/bench_sglang.py \
  --port 30000 \
  --concurrency 64 \
  --extra-request-body '{"max_tokens": 4096}'
```

## Thinking Mode

For reasoning models (Qwen3, DeepSeek-V3):

```bash
python -m sglang.test.run_eval \
  --eval-name gpqa \
  --port 30000 \
  --thinking-mode qwen3
```

Supported modes:
- `qwen3`
- `deepseek-v3`

## Recommended Evaluation Suite

For comprehensive model evaluation:

1. **GPQA** - Advanced reasoning
2. **MMLU** - Broad knowledge
3. **GSM8K** - Math reasoning
4. **HumanEval** - Code generation
5. **Latency benchmark** - Interactive performance
6. **Throughput benchmark** - Production capacity

## Result Interpretation

### Accuracy Scores

| Benchmark | Good | Excellent | State-of-Art |
|-----------|------|-----------|--------------|
| GPQA | 40% | 55% | 65%+ |
| MMLU | 60% | 75% | 85%+ |
| GSM8K | 70% | 85% | 95%+ |
| HumanEval | 40% | 60% | 80%+ |

### Performance Metrics

| Metric | Good | Excellent |
|--------|------|-----------|
| TTFT | <500ms | <200ms |
| Throughput | >100 tok/s | >500 tok/s |

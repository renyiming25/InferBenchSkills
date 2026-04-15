# JSON 结果文件格式说明

本文档描述 `sglang-model-eval` 生成的 JSON 结果文件格式。

## 文件命名

```
<模型名>_<时间戳>.json
```

示例：`Qwen3.5-0.8B_20260413_121747.json`

## 完整结构

```json
{
  "status": "success",
  "model_id": "/workspace/models/Qwen3.5-0.8B",
  "model_name": "Qwen3.5-0.8B",
  "evaluation_time": "2026-04-13T12:12:19.491988",
  "environment": {
    "tp_size": 1,
    "port": 30000,
    "gpu": "NVIDIA A100-PCIE-40GB, 40960 MiB",
    "sglang_version": "0.5.10rc0"
  },
  "benchmarks": {
    "gpqa": {
      "accuracy": 0.328,
      "samples": 198,
      "max_tokens": 32768,
      "duration_seconds": 553.21
    },
    "mmlu": {
      "accuracy": 0.488,
      "samples": 1000,
      "duration_seconds": 560.14
    },
    "gsm8k": {
      "accuracy": 0.335,
      "samples": 200,
      "duration_seconds": 21.4
    },
    "humaneval": {
      "accuracy": 0.316,
      "samples": 164,
      "duration_seconds": 124.47
    },
    "hellaswag": {
      "accuracy": 0.58,
      "samples": 200,
      "duration_seconds": 56.27
    }
  },
  "performance": {
    "latency": {
      "ttft_ms": 346.72,
      "num_prompts": 10,
      "random_input_len": 32000,
      "random_output_len": 500
    },
    "throughput": {
      "total_throughput_tokens_per_sec": 35129.17,
      "input_throughput_tokens_per_sec": 34590.58,
      "output_throughput_tokens_per_sec": 538.59,
      "qps": 2.16,
      "concurrency": 100,
      "successful_requests": 500,
      "mean_e2e_latency_ms": 45285.24
    },
    "throughput_multi": {
      "concurrency_5": { ... },
      "concurrency_10": { ... }
    }
  },
  "errors": [],
  "log_file": "/workspace/eval_logs/model_eval_20260413.log",
  "benchmark_log_dir": "/workspace/eval_logs/benchmarks",
  "total_duration_seconds": 328.29
}
```

## 字段说明

### 顶层字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | 评估状态：`success`、`partial`、`error` |
| `model_id` | string | 模型完整路径或 ID |
| `model_name` | string | 模型名称（从路径提取） |
| `evaluation_time` | string | 评估时间（ISO 8601 格式） |
| `environment` | object | 环境信息 |
| `benchmarks` | object | 基准测试结果 |
| `performance` | object | 性能测试结果 |
| `errors` | array | 错误信息列表 |
| `log_file` | string | 主日志文件路径 |
| `benchmark_log_dir` | string | 基准测试日志目录 |
| `total_duration_seconds` | number | 总耗时（秒） |

### environment 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `tp_size` | int | Tensor 并行数 |
| `port` | int | SGLang 服务端口 |
| `gpu` | string | GPU 信息 |
| `sglang_version` | string | SGLang 版本 |

### benchmarks 字段

每个基准测试包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `accuracy` | float | 准确率（0-1 范围） |
| `samples` | int | 测试样本数 |
| `duration_seconds` | number | 测试耗时（秒） |
| `max_tokens` | int | 最大生成 token 数（可选） |

支持的基准测试：
- `gpqa` - 研究生级别推理
- `mmlu` - 多任务语言理解
- `gsm8k` - 数学推理
- `humaneval` - 代码生成
- `hellaswag` - 常识推理

### performance 字段

#### latency（延迟测试）

| 字段 | 类型 | 说明 |
|------|------|------|
| `ttft_ms` | number | 首 Token 延迟（毫秒） |
| `num_prompts` | int | 测试请求数 |
| `random_input_len` | int | 随机输入长度 |
| `random_output_len` | int | 随机输出长度 |

#### throughput（吞吐量测试）

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_throughput_tokens_per_sec` | number | 总吞吐量（tokens/s） |
| `input_throughput_tokens_per_sec` | number | 输入吞吐量 |
| `output_throughput_tokens_per_sec` | number | 输出吞吐量 |
| `qps` | number | 每秒请求数 |
| `concurrency` | int | 并发数 |
| `successful_requests` | int | 成功请求数 |
| `mean_e2e_latency_ms` | number | 平均端到端延迟 |

#### throughput_multi（多并发吞吐量测试）

包含多个并发级别的测试结果，键名格式为 `concurrency_<N>`。

## 状态值说明

| 状态 | 说明 |
|------|------|
| `success` | 所有测试成功完成 |
| `partial` | 部分测试成功，有测试失败 |
| `error` | 评估过程出错 |
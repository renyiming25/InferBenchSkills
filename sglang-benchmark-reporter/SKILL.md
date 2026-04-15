---
name: sglang-benchmark-reporter
description: |
  读取 sglang-model-eval 的评估结果 JSON 文件，生成结构化的自测报告。
  支持单个模型报告和多模型对比报告。

  触发场景：
  - 用户需要查看模型评估结果报告
  - 用户提到：生成报告、评估报告、benchmark报告、测试报告
  - 用户需要对比多个模型的评估结果
  - 用户需要汇总评估数据
---

# SGLang Benchmark Reporter

读取 sglang-model-eval 的评估结果 JSON 文件，生成结构化报告。

## 快速开始

```bash
# 生成单个模型的报告
python3 scripts/generate_report.py --report_dir /workspace/eval_reports

# 指定模型名称筛选
python3 scripts/generate_report.py --report_dir /workspace/eval_reports --model Qwen3.5-0.8B

# 生成多模型对比报告
python3 scripts/generate_report.py --report_dir /workspace/eval_reports --compare

# 指定输出文件
python3 scripts/generate_report.py --report_dir /workspace/eval_reports --output /workspace/reports/summary.md
```

## 参数说明

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `--report_dir` | 否 | `/workspace/eval_reports` | 评估结果 JSON 文件目录 |
| `--model` | 否 | - | 筛选指定模型（支持模糊匹配） |
| `--compare` | 否 | - | 生成多模型对比报告 |
| `--output` | 否 | 自动生成 | 输出文件路径 |
| `--format` | 否 | `markdown` | 输出格式：`markdown` 或 `json` |
| `--latest` | 否 | - | 只使用每个模型的最新结果 |

## 输出格式

### 单模型报告

```markdown
# 模型评估报告: Qwen3.5-0.8B

## 基本信息
- 模型路径: /workspace/models/Qwen3.5-0.8B
- 评估时间: 2026-04-13T12:12:19
- 评估状态: success
- 总耗时: 328.29s

## 环境信息
- GPU: NVIDIA A100-PCIE-40GB
- SGLang 版本: 0.5.10rc0
- TP Size: 1

## 基准测试结果
| Benchmark | Accuracy | Samples | Duration |
|-----------|----------|---------|----------|
| GPQA | 32.80% | 198 | 553.21s |
| MMLU | 48.80% | 1000 | 560.14s |

## 性能测试结果
| 指标 | 值 |
|------|-----|
| TTFT (延迟) | 346.72ms |
| 吞吐量 | 35129.17 tokens/s |
| QPS | 2.16 |
```

### 多模型对比报告

```markdown
# 模型评估对比报告

## 基准测试对比
| Model | GPQA | MMLU | GSM8K | HumanEval | HellaSwag |
|-------|------|------|-------|-----------|-----------|
| Qwen3-0.6B | 25.80% | - | - | - | - |
| Qwen3.5-0.8B | 32.80% | 48.80% | 33.50% | 31.60% | 58.00% |
| Qwen3.5-2B | 53.00% | 67.70% | 57.50% | 48.90% | 66.00% |

## 性能对比
| Model | TTFT (ms) | Throughput (tokens/s) |
|-------|-----------|----------------------|
| Qwen3-0.6B | 222.23 | 21404.02 |
| Qwen3.5-0.8B | 346.72 | 35129.17 |
```

## JSON 结果文件格式

脚本读取的 JSON 文件格式：

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
      "duration_seconds": 553.21
    }
  },
  "performance": {
    "latency": {
      "ttft_ms": 346.72
    },
    "throughput": {
      "total_throughput_tokens_per_sec": 35129.17
    }
  },
  "errors": [],
  "total_duration_seconds": 328.29
}
```

## 报告类型

### 1. 单模型详细报告

包含模型的完整评估信息：
- 基本信息
- 环境配置
- 基准测试详细结果
- 性能测试详细结果
- 错误信息（如有）

### 2. 多模型对比报告

横向对比多个模型：
- 基准测试准确率对比表
- 性能指标对比表
- 最佳模型标注

### 3. 汇总统计报告

统计所有评估结果：
- 评估次数
- 模型列表
- 平均准确率
- 性能范围

## 使用示例

### 查看最新评估结果

```bash
python3 scripts/generate_report.py --latest
```

### 对比 Qwen 系列模型

```bash
python3 scripts/generate_report.py --model Qwen --compare
```

### 导出 JSON 格式

```bash
python3 scripts/generate_report.py --format json --output results.json
```

## 与 sglang-model-eval 配合使用

```bash
# 1. 运行评估
python3 /path/to/sglang-model-eval/scripts/eval_model.py \
  --model_path Qwen3.5-0.8B --all

# 2. 生成报告
python3 scripts/generate_report.py --model Qwen3.5-0.8B
```

## 日志文件

报告生成日志: `/workspace/eval_logs/report_generator.log`
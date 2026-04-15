# SGLang Benchmark Reporter Skill 方案

## 概述

`sglang-benchmark-reporter` 是一个用于读取 `sglang-model-eval` 评估结果 JSON 文件并生成结构化报告的 skill。

## 目录结构

```
.claude/skills/sglang-benchmark-reporter/
├── SKILL.md                    # Skill 定义文档
├── scripts/
│   └── generate_report.py      # 报告生成脚本
└── references/
    └── json_schema.md          # JSON 结果文件格式说明
```

## 核心功能

### 1. 单模型报告

生成单个模型的详细评估报告，包含：
- 基本信息（模型路径、评估时间、状态）
- 环境信息（GPU、SGLang 版本、TP Size）
- 基准测试结果表格
- 性能测试结果（延迟、吞吐量）
- 错误信息（如有）

### 2. 多模型对比报告

横向对比多个模型的评估结果：
- 基准测试准确率对比表
- 性能指标对比表
- 各模型详细信息

### 3. 汇总统计报告

统计所有评估结果：
- 评估次数统计
- 模型列表
- 最近评估历史

## 使用方式

```bash
# 生成单个模型报告
python3 scripts/generate_report.py --model Qwen3.5-0.8B

# 生成多模型对比报告
python3 scripts/generate_report.py --compare --latest

# 生成汇总统计报告
python3 scripts/generate_report.py --summary

# 指定输出文件
python3 scripts/generate_report.py --compare --output /workspace/reports/compare.md
```

## 参数说明

| 参数 | 说明 |
|------|------|
| `--report_dir` | 评估结果 JSON 文件目录（默认: `/workspace/eval_reports`） |
| `--model` | 筛选指定模型（支持模糊匹配） |
| `--compare` | 生成多模型对比报告 |
| `--summary` | 生成汇总统计报告 |
| `--latest` | 只使用每个模型的最新结果 |
| `--output` | 输出文件路径 |
| `--format` | 输出格式：`markdown` 或 `json` |

## 输入数据格式

脚本读取 `sglang-model-eval` 生成的 JSON 结果文件：

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
    },
    "mmlu": {
      "accuracy": 0.488,
      "samples": 1000,
      "duration_seconds": 560.14
    }
  },
  "performance": {
    "latency": {
      "ttft_ms": 346.72,
      "num_prompts": 10
    },
    "throughput": {
      "total_throughput_tokens_per_sec": 35129.17,
      "qps": 2.16,
      "concurrency": 100
    }
  },
  "errors": [],
  "total_duration_seconds": 328.29
}
```

## 输出示例

### 单模型报告

```markdown
# 模型评估报告: Qwen3.5-0.8B

## 基本信息
- **模型路径**: /workspace/models/Qwen3.5-0.8B
- **评估时间**: 2026-04-13T12:12:19
- **评估状态**: success
- **总耗时**: 328.29s

## 环境信息
- **GPU**: NVIDIA A100-PCIE-40GB
- **SGLang 版本**: 0.5.10rc0
- **TP Size**: 1

## 基准测试结果
| Benchmark | Accuracy | Samples | Duration |
|-----------|----------|---------|----------|
| GPQA | 32.80% | 198 | 553.21s |
| MMLU | 48.80% | 1000 | 560.14s |

## 性能测试结果
| 指标 | 值 |
|------|-----|
| TTFT (首Token延迟) | 346.72 ms |
| 总吞吐量 | 35129.17 tokens/s |
| QPS | 2.16 |
```

### 多模型对比报告

```markdown
# 模型评估对比报告

**生成时间**: 2026-04-14T03:42:03
**模型数量**: 3

## 基准测试对比
| Model | GPQA | MMLU | GSM8K | HumanEval | HellaSwag |
|-------|------|------|-------|-----------|-----------|
| Qwen3-0.6B | 25.80% | - | - | - | - |
| Qwen3.5-0.8B | 32.80% | 48.80% | 33.50% | 31.60% | 58.00% |
| Qwen3.5-2B | 53.00% | 67.70% | 57.50% | 48.90% | 66.00% |

## 性能对比
| Model | TTFT (ms) | Throughput (tokens/s) | QPS |
|-------|-----------|----------------------|-----|
| Qwen3-0.6B | 222.23 | 21404.02 | 1.32 |
| Qwen3.5-0.8B | 346.72 | 35129.17 | 2.16 |
```

## 与 sglang-model-eval 的关系

```
┌─────────────────────────┐     ┌─────────────────────────────┐
│  sglang-model-eval      │     │  sglang-benchmark-reporter  │
├─────────────────────────┤     ├─────────────────────────────┤
│  运行评估测试           │     │  读取评估结果               │
│  ↓                      │     │  ↓                          │
│  生成 JSON 结果文件     │ ──→ │  生成结构化报告             │
│  ↓                      │     │  ↓                          │
│  /workspace/eval_reports│     │  Markdown / JSON 输出       │
└─────────────────────────┘     └─────────────────────────────┘
```

## 扩展性

### 添加新的报告类型

在 `generate_report.py` 中添加新的生成函数：

```python
def generate_custom_report(results: List[Dict]) -> str:
    """自定义报告格式"""
    # 实现自定义报告逻辑
    pass
```

### 支持新的数据格式

修改 `load_json_files` 函数以支持其他格式的输入文件。

## 后续优化

1. **图表生成**: 集成 matplotlib 生成可视化图表
2. **HTML 报告**: 支持 HTML 格式的交互式报告
3. **历史趋势**: 支持查看模型评估结果的历史变化趋势
4. **自动归档**: 自动归档旧报告，保持目录整洁
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

SGLang 模型评估 Skill，用于自动化评估模型效果。支持准确性测试（GPQA、MMLU、GSM8K、HumanEval、HellaSwag）和性能测试（延迟、吞吐量）。

## 核心脚本

```bash
# 完整评估（返回 JSON 结果）
python3 scripts/eval_model.py --model_path Qwen/Qwen2.5-7B-Instruct

# 指定基准测试
python3 scripts/eval_model.py --model_path <MODEL> --benchmarks gpqa,mmlu,gsm8k

# Markdown 报告
python3 scripts/eval_model.py --model_path <MODEL> --output markdown
```

## 输出结构

脚本返回结构化 JSON：
- `status`: success/partial/error
- `benchmarks`: 各基准测试的准确率
- `performance`: TTFT 和吞吐量
- `report_path`: 报告文件路径

## 辅助脚本

- `scripts/run_benchmark.sh`: Shell wrapper，适合手动执行
- `scripts/quick_eval.sh`: 快速单测试，需服务器已运行

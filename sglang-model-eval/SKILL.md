---
name: sglang-model-eval
description: |
  自动化评估模型效果。使用 SGLang 框架运行基准测试（GPQA、MMLU、GSM8K、HumanEval、HellaSwag）
  和性能测试（延迟、吞吐量），生成结构化评估报告。

  触发场景：
  - 用户需要评估新模型的准确性或性能
  - 用户提到：模型评估、benchmark测试、accuracy测试、模型验证、SGLang eval
  - 用户需要对比多个模型的效果
  - 用户需要生成模型评估报告
---

# SGLang 模型评估 Skill

自动化评估模型效果，支持准确性测试和性能测试，生成结构化报告。

## 快速开始

```bash
# 默认只运行 GPQA 基准测试（前台运行）
python3 scripts/eval_model.py --model_path Qwen3.5-0.8B --foreground

# 后台运行（推荐用于长时间评估任务，默认后台模式）
python3 scripts/eval_model.py --model_path Qwen3.5-0.8B --all

# 运行全部基准测试
python3 scripts/eval_model.py --model_path Qwen3.5-0.8B --all --foreground

# 或者使用 --benchmarks all
python3 scripts/eval_model.py --model_path Qwen3.5-0.8B --benchmarks all --foreground

# 指定部分基准测试
python3 scripts/eval_model.py --model_path Qwen3.5-0.8B --benchmarks gpqa,mmlu --foreground

# 仅运行性能测试（不运行基准测试）
python3 scripts/eval_model.py --model_path Qwen3.5-0.8B --performance_only --foreground

# 运行基准测试 + 性能测试
python3 scripts/eval_model.py --model_path Qwen3.5-0.8B --benchmarks gpqa --performance --foreground

# 使用 HuggingFace/ModelScope ID（本地不存在则自动下载）
python3 scripts/eval_model.py --model_path Qwen/Qwen2.5-7B-Instruct --foreground

# 使用本地绝对路径
python3 scripts/eval_model.py --model_path /workspace/models/Qwen2.5-7B-Instruct --foreground

# 指定输出格式
python3 scripts/eval_model.py --model_path Qwen3.5-0.8B --output markdown --foreground
```

## 后台运行模式

默认为后台运行模式，长时间评估任务会自动在后台执行：

```bash
# 后台运行全部测试（默认模式）
python3 scripts/eval_model.py --model_path Qwen3.5-0.8B --all
```

启动后会显示：
```
============================================================
启动后台评估任务
============================================================
模型: Qwen3.5-0.8B
基准测试: gpqa,mmlu,gsm8k,humaneval,hellaswag
日志文件: /workspace/eval_logs/model_eval_20260310.log
PID 文件: /workspace/eval_logs/eval_model.pid
============================================================

✓ 任务已启动 (PID: 12345)

查看进度:
  tail -f /workspace/eval_logs/model_eval_20260310.log

检查任务状态:
  ps -p 12345

停止任务:
  kill 12345
```

### 前台运行

如需前台运行（实时查看输出），使用 `--foreground` 参数：

```bash
python3 scripts/eval_model.py --model_path Qwen3.5-0.8B --all --foreground
```

### 后台任务管理

```bash
# 查看日志
tail -f /workspace/eval_logs/model_eval_20260310.log

# 检查任务是否在运行
cat /workspace/eval_logs/eval_model.pid
ps -p $(cat /workspace/eval_logs/eval_model.pid)

# 停止任务
kill $(cat /workspace/eval_logs/eval_model.pid)
```

## 模型路径解析

`--model_path` 参数支持多种格式：

| 格式 | 示例 | 说明 |
|------|------|------|
| 模型名称 | `Qwen3.5-0.8B` | 自动在 `/workspace/models` 下查找，不存在则从 ModelScope 下载 |
| ModelScope ID | `Qwen/Qwen2.5-7B-Instruct` | 本地存在则使用，否则自动下载 |
| 本地路径 | `/workspace/models/Qwen2.5-7B-Instruct` | 直接使用指定路径 |

### 模型下载目录

默认下载目录: `/workspace/models`

可通过 `--model_dir` 参数修改：
```bash
python3 scripts/eval_model.py --model_path Qwen3.5-0.8B --model_dir /data/models
```

## 参数说明

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `--model_path` | 是 | - | 模型路径、ID 或名称（见模型路径解析） |
| `--model_dir` | 否 | `/workspace/models` | 模型下载目录 |
| `--benchmarks` | 否 | `gpqa` | 要运行的基准测试，逗号分隔。使用 `none` 跳过基准测试 |
| `--all` | 否 | - | 运行全部基准测试 |
| `--foreground` | 否 | - | 前台运行模式（默认后台运行） |
| `--performance` | 否 | - | 运行性能测试（延迟、吞吐量） |
| `--performance-only` | 否 | - | 仅运行性能测试，跳过所有基准测试 |
| `--output` | 否 | `json` | 输出格式：`json` 或 `markdown` |
| `--report_path` | 否 | 自动生成 | 报告保存路径 |
| `--port` | 否 | `30000` | SGLang 服务端口 |
| `--tp` | 否 | `1` | Tensor 并行数 |
| `--num_examples` | 否 | 见下表 | 各基准测试样本数 |
| `--thinking_mode` | 否 | - | 推理模式：`qwen3` 或 `deepseek-v3` |
| `--random_input_len` | 否 | `32000` | 性能测试随机输入长度 |
| `--random_output_len` | 否 | `500` | 性能测试随机输出长度 |

### 默认样本数

| Benchmark | 默认样本数 |
|-----------|-----------|
| gpqa | 198 |
| mmlu | 1000 |
| gsm8k | 200 |
| humaneval | 164 |
| hellaswag | 200 |

## 输出格式

### JSON 输出

```json
{
  "status": "success",
  "model_id": "Qwen/Qwen2.5-7B-Instruct",
  "evaluation_time": "2026-03-10T12:00:00",
  "environment": {
    "gpu": "NVIDIA A100 80GB",
    "sglang_version": "0.4.0",
    "tp_size": 1
  },
  "benchmarks": {
    "gpqa": {
      "accuracy": 0.52,
      "samples": 198,
      "duration_seconds": 120
    },
    "mmlu": {
      "accuracy": 0.72,
      "samples": 1000,
      "duration_seconds": 300
    },
    "gsm8k": {
      "accuracy": 0.85,
      "samples": 200,
      "duration_seconds": 180
    }
  },
  "performance": {
    "ttft_ms": 234,
    "throughput_tokens_per_sec": 156
  },
  "report_path": "/workspace/eval_reports/Qwen2.5-7B-Instruct_20260310.md"
}
```

### Markdown 报告

自动生成包含以下内容的报告：
- 模型信息和环境配置
- 各基准测试结果表格
- 性能指标
- 与参考值的对比

## 支持的基准测试

| Benchmark | 类型 | 说明 |
|-----------|------|------|
| `gpqa` | 准确性 | 研究生级别推理测试 |
| `mmlu` | 准确性 | 多任务语言理解 |
| `gsm8k` | 准确性 | 数学推理 |
| `humaneval` | 准确性 | 代码生成 |
| `hellaswag` | 准确性 | 常识推理 |

### 单独运行基准测试

```bash
# 仅运行 GPQA
python3 scripts/eval_model.py --model_path Qwen3-0.6B --benchmarks gpqa --foreground

# 仅运行 MMLU
python3 scripts/eval_model.py --model_path Qwen3-0.6B --benchmarks mmlu --foreground

# 仅运行 GSM8K
python3 scripts/eval_model.py --model_path Qwen3-0.6B --benchmarks gsm8k --foreground

# 运行多个基准测试
python3 scripts/eval_model.py --model_path Qwen3-0.6B --benchmarks gpqa,mmlu,gsm8k --foreground
```

## 性能测试

默认运行两项性能测试：

1. **延迟测试 (TTFT)**: 单请求首 token 延迟
2. **吞吐量测试**: 高并发下的 tokens/second

### 性能测试示例

```bash
# 仅运行性能测试（不运行基准测试）
python3 scripts/eval_model.py --model_path Qwen3-0.6B --performance_only --foreground

# 运行基准测试 + 性能测试
python3 scripts/eval_model.py --model_path Qwen3-0.6B --benchmarks gpqa --performance --foreground

# 使用 --benchmarks none 跳过基准测试，仅运行性能测试
python3 scripts/eval_model.py --model_path Qwen3-0.6B --benchmarks none --performance --foreground
```

## 推理模型

对于支持 thinking 的模型（如 Qwen3、DeepSeek-V3）：

```bash
python3 scripts/eval_model.py \
  --model_path Qwen/Qwen3-32B \
  --thinking_mode qwen3
```

## 工作流程

1. **启动 SGLang 服务器**: 自动启动并等待就绪
2. **运行基准测试**: 按顺序执行指定的测试
3. **运行性能测试**: 测量延迟和吞吐量
4. **生成报告**: 汇总结果并保存
5. **清理资源**: 关闭服务器

## 依赖

```bash
pip install sglang[all] -i https://pypi.mirrors.ustc.edu.cn/simple
pip install human_eval -i https://pypi.mirrors.ustc.edu.cn/simple  # HumanEval 测试需要
```

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `scripts/eval_model.py` | 核心评估脚本，支持自动下载模型、结构化输出 |
| `scripts/quick_eval.sh` | 快速单测试，需服务器已运行 |

## 日志文件

评估过程全程记录到日志文件：

| 文件 | 路径 |
|------|------|
| 评估日志 | `/workspace/eval_logs/model_eval_<日期>.log` |
| 服务器日志 | `/workspace/eval_logs/sglang_server_<端口>.log` |
| 评估报告 | `/workspace/eval_reports/<模型名>_<时间戳>.json` |

## 故障排查

### 服务器启动失败

检查 GPU 内存是否足够：
```bash
nvidia-smi
```

调整内存占用：
```bash
python3 scripts/eval_model.py --model_path <MODEL> --mem_fraction 0.7
```

### 基准测试超时

减少样本数：
```bash
python3 scripts/eval_model.py --model_path <MODEL> --num_examples gpqa:50,mmlu:100
```

## 参考

- [SGLang 评估文档](https://docs.sglang.ai/developer_guide/evaluating_new_models.html)
- `references/benchmarks.md` - 详细基准测试说明

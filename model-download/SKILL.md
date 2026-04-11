---
name: model-download
description: |
  从 ModelScope 或 HuggingFace 下载 AI 模型。支持多级下载策略：优先使用 ModelScope CLI，失败则尝试 HuggingFace CLI，最后使用 ModelScope Python SDK。
  支持后台下载、日志记录和下载完成后的简要总结。当用户需要下载模型时使用此 skill。
---

# 模型下载 Skill

从 ModelScope 或 HuggingFace 下载 AI 模型，支持多级下载策略和后台下载。

## 下载策略

按以下优先级顺序尝试下载：

1. **ModelScope CLI** - 默认优先使用
   ```bash
   modelscope download --model Qwen/Qwen2.5-7B-Instruct --local_dir ./Qwen2.5-7B-Instruct
   ```

2. **HuggingFace CLI** - 如果 ModelScope 失败则尝试
   ```bash
   export HF_ENDPOINT=https://hf-mirror.com
   huggingface-cli download --resume-download Qwen/Qwen3-Coder-Next --local-dir ./ --local-dir-use-symlinks False --token xxx
   ```

3. **ModelScope Python SDK** - 如果前两种方法都失败则使用
   ```python
   from modelscope import snapshot_download
   snapshot_download(model_id="Qwen/Qwen2.5-7B-Instruct", local_dir="/workspace/models/Qwen2.5-7B-Instruct")
   ```

## Quick Start

```bash
python3 plugin/download_model_skill.py --model_id Qwen/Qwen2.5-7B-Instruct
```

## Usage

### 基本下载（后台下载）

```bash
python3 plugin/download_model_skill.py --model_id Qwen/Qwen2.5-7B-Instruct
```

默认情况下，模型会在后台下载，脚本会立即返回。下载进度和日志会记录在 `{save_path}/download_log.txt` 文件中。

### 同步下载（等待完成）

```bash
python3 plugin/download_model_skill.py --model_id Qwen/Qwen2.5-7B-Instruct --no-background
```

使用 `--no-background` 参数可以同步下载，脚本会等待下载完成后才返回。

### 下载到指定路径

```bash
python3 plugin/download_model_skill.py --model_id Qwen/Qwen2.5-7B-Instruct --save_path ./my_models
```

### 使用 HuggingFace Token

```bash
python3 plugin/download_model_skill.py --model_id username/private-model --token YOUR_HF_TOKEN
```

或者通过环境变量设置：

```bash
export HF_TOKEN=YOUR_HF_TOKEN
python3 plugin/download_model_skill.py --model_id username/private-model
```

### 等待后台下载完成

```bash
python3 plugin/download_model_skill.py --model_id Qwen/Qwen2.5-7B-Instruct --wait-timeout 3600
```

使用 `--wait-timeout` 参数可以等待后台下载完成，超时时间以秒为单位。

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--model_id` | Yes | - | 模型标识符（例如: `Qwen/Qwen2.5-7B-Instruct`） |
| `--save_path` | No | Auto-generated | 本地保存目录路径（未提供则自动生成） |
| `--token` | No | - | HuggingFace 认证令牌（也可通过 `HF_TOKEN` 环境变量设置） |
| `--no-background` | No | `false` | 同步下载（等待完成），默认是后台下载 |
| `--wait-timeout` | No | - | 等待后台下载完成的超时时间（秒） |

## Features

### 1. 多级下载策略
自动尝试多种下载方法，确保最大成功率：
- ModelScope CLI（优先）
- HuggingFace CLI（备选）
- ModelScope Python SDK（最后备选）

### 2. 后台下载
默认在后台下载模型，不阻塞主进程。下载进度实时记录到日志文件。

### 3. 日志记录
所有下载过程都会记录到 `{save_path}/download_log.txt` 文件中，包括：
- 下载开始时间
- 每个策略的尝试结果
- 命令执行输出
- 错误信息
- 下载完成状态

### 4. 简要总结
下载完成后，可以从日志文件中提取关键信息生成简要总结，包括：
- 模型 ID 和保存路径
- 使用的下载方法
- 下载状态
- 关键错误信息

### 5. 自动目录创建
自动创建目标目录（如果不存在）。

### 6. 目录命名规则
模型下载到本地的目录规则：
- 模型 ID: `Qwen/Qwen2.5-7B-Instruct`
- 本地目录: `/workspace/models/Qwen2.5-7B-Instruct`
- 规则：只取模型名的最后一部分（去掉组织名），保留点号和连字符

## Output

脚本返回包含以下信息的字典：

- **status**: 下载状态（`success`, `error`, `pending`）
- **model_id**: 模型标识符
- **save_path**: 保存路径
- **method**: 使用的下载方法（`modelscope-cli`, `huggingface-cli`, `modelscope-python`）
- **messages**: 消息列表
- **errors**: 错误列表
- **log_file**: 日志文件路径
- **summary**: 下载日志简要总结（同步下载时可用）

### 后台下载示例输出

```json
{
  "status": "pending",
  "model_id": "Qwen/Qwen2.5-7B-Instruct",
  "save_path": "/workspace/models/Qwen2.5-7B-Instruct",
  "messages": [
    "开始下载模型 Qwen/Qwen2.5-7B-Instruct 到 /workspace/models/Qwen2.5-7B-Instruct",
    "模型正在后台下载中...",
    "下载任务已启动，请稍后查看日志文件获取进度"
  ],
  "log_file": "/workspace/models/Qwen2.5-7B-Instruct/download_log.txt"
}
```

### 同步下载示例输出

```json
{
  "status": "success",
  "model_id": "Qwen/Qwen2.5-7B-Instruct",
  "save_path": "/workspace/models/Qwen2.5-7B-Instruct",
  "method": "modelscope-cli",
  "messages": [
    "开始下载模型 Qwen/Qwen2.5-7B-Instruct 到 /workspace/models/Qwen2.5-7B-Instruct",
    "✓ 使用 ModelScope CLI 下载成功"
  ],
  "log_file": "/workspace/models/Qwen2.5-7B-Instruct/download_log.txt",
  "summary": "模型下载日志\n...\n下载状态: 成功 (方法: ModelScope CLI)"
}
```

## 日志文件格式

日志文件 `download_log.txt` 包含以下信息：

```
模型下载日志
============================================================
模型 ID: Qwen/Qwen2.5-7B-Instruct
保存路径: /workspace/models/Qwen2.5-7B-Instruct
开始时间: 2024-01-01T12:00:00.000000

2024-01-01 12:00:00 - 开始下载模型 Qwen/Qwen2.5-7B-Instruct 到 /workspace/models/Qwen2.5-7B-Instruct
2024-01-01 12:00:01 - ============================================================
2024-01-01 12:00:01 - 策略 1: 使用 ModelScope CLI 下载
2024-01-01 12:00:01 - 尝试使用 ModelScope CLI 下载...
2024-01-01 12:00:01 - 执行命令: modelscope download --model Qwen/Qwen2.5-7B-Instruct --local_dir /workspace/models/Qwen2.5-7B-Instruct
...
2024-01-01 12:05:00 - ModelScope CLI 下载成功
2024-01-01 12:05:00 - ============================================================
2024-01-01 12:05:00 - 下载状态: 成功 (方法: ModelScope CLI)
```

## Common Use Cases

- **模型开发**: 下载模型用于微调或研究
- **私有模型**: 使用认证令牌访问受限模型
- **本地部署**: 缓存模型用于离线使用
- **模型测试**: 下载并测试多个模型变体
- **批量下载**: 后台下载多个模型，不阻塞主进程

## 依赖要求

### 必需工具

- **ModelScope CLI**: 用于策略1和策略3
  ```bash
  pip install modelscope
  ```

- **HuggingFace CLI**: 用于策略2
  ```bash
  pip install huggingface_hub[cli]
  ```

### Python 包

- `modelscope` - ModelScope Python SDK
- `huggingface_hub` - HuggingFace Python SDK（可选，用于策略2）

## 环境变量

- `MODEL_DIR`: 默认模型保存目录（默认: `/workspace/models`）
- `HF_ENDPOINT`: HuggingFace 端点（默认: `https://hf-mirror.com`）
- `HF_TOKEN`: HuggingFace 认证令牌（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）

## 目录规则

模型下载到本地的目录规则：
- **模型 ID**: `Qwen/Qwen2.5-7B-Instruct`
- **本地目录**: `/workspace/models/Qwen2.5-7B-Instruct`
- **规则说明**: 只取模型名的最后一部分（去掉组织名），保留点号和连字符等合法字符

示例：
- `Qwen/Qwen2.5-7B-Instruct` → `/workspace/models/Qwen2.5-7B-Instruct`
- `deepseek-ai/deepseek-llm-7b-chat` → `/workspace/models/deepseek-llm-7b-chat`
- `bert-base-uncased` → `/workspace/models/bert-base-uncased`

## Notes

- 默认使用 ModelScope CLI 下载，如果模型在 ModelScope 不存在，会自动尝试 HuggingFace
- 大型模型可能需要较长时间下载，建议使用后台下载模式
- 日志文件会实时更新，可以随时查看下载进度
- 如果所有下载策略都失败，会返回详细的错误信息
- 下载完成后，可以通过日志文件获取完整的下载过程记录

## 参考
- modelscope CLI 下载参考：https://www.modelscope.cn/docs/models/download
- HuggingFace CLI 下载参考: https://github.com/huggingface/skills/blob/main/skills/hugging-face-cli/SKILL.md

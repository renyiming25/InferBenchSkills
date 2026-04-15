---
name: model-download
description: |
  从 ModelScope 或 HuggingFace 下载 AI 模型。支持多级下载策略、指定下载源、文件大小预估和后台下载。
  当用户需要下载模型时使用此 skill。
---

# 模型下载 Skill

从 ModelScope 或 HuggingFace 下载 AI 模型，支持多级下载策略、文件大小预估和后台下载。

## 快速开始

```bash
# 下载模型（后台下载，自动选择源）
python3 scripts/download_model_skill.py --model_id Qwen/Qwen2.5-7B-Instruct

# 指定下载源
python3 scripts/download_model_skill.py --model_id Qwen/Qwen2.5-7B-Instruct --source huggingface

# 同步下载（等待完成）
python3 scripts/download_model_skill.py --model_id Qwen/Qwen2.5-7B-Instruct --no-background
```

## 参数说明

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `--model_id` | ✅ | - | 模型标识符（如 `Qwen/Qwen2.5-7B-Instruct`） |
| `--save_path` | ❌ | 自动生成 | 本地保存目录 |
| `--source` | ❌ | `auto` | 下载源：`auto`/`modelscope`/`huggingface` |
| `--token` | ❌ | 环境变量 | HuggingFace 认证令牌 |
| `--no-background` | ❌ | `false` | 同步下载（等待完成） |
| `--wait-timeout` | ❌ | - | 等待后台下载的超时时间（秒） |

## 下载策略

根据 `--source` 参数选择下载策略：

| source | 策略顺序 |
|--------|----------|
| `auto` | ModelScope CLI → HuggingFace CLI → ModelScope Python SDK |
| `modelscope` | ModelScope CLI → ModelScope Python SDK |
| `huggingface` | HuggingFace CLI |

## 功能特性

### 文件大小预估

下载前自动从 HuggingFace API 获取模型大小，帮助预估下载时间。

### 智能进度日志

减少日志频率，避免日志文件过大：
- 进度更新：每 **20%** 或每 **10 分钟** 记录一次
- 关键信息：始终记录（开始、完成、错误等）

### 后台下载

默认后台下载，不阻塞主进程。日志实时记录到 `{save_path}/model_download.txt`。

### 多级策略

自动尝试多种下载方法，确保最大成功率。

## 目录规则

模型下载到本地的目录命名规则：
- 模型 ID: `Qwen/Qwen2.5-7B-Instruct`
- 本地目录: `/workspace/models/Qwen2.5-7B-Instruct`
- 规则：只取模型名的最后一部分（去掉组织名）

示例：
| 模型 ID | 本地目录 |
|--------|----------|
| `Qwen/Qwen2.5-7B-Instruct` | `/workspace/models/Qwen2.5-7B-Instruct` |

## 查看下载进度

```bash
# 查看最新 15 行日志
tail -15 /workspace/models/{model_name}/model_download.txt

# 实时查看日志
tail -f /workspace/models/{model_name}/model_download.txt
```

## 输出示例

```
预估模型大小: 15.23 GB

============================================================
模型下载结果
============================================================
模型 ID: Qwen/Qwen2.5-7B-Instruct
保存路径: /workspace/models/Qwen2.5-7B-Instruct
预估大小: 15.23 GB
状态: SUCCESS
下载方法: modelscope-cli

消息:
  开始下载模型 Qwen/Qwen2.5-7B-Instruct 到 /workspace/models/Qwen2.5-7B-Instruct
  ✓ 使用 ModelScope CLI 下载成功

下载日志摘要:
模型 ID: Qwen/Qwen2.5-7B-Instruct
保存路径: /workspace/models/Qwen2.5-7B-Instruct
预估大小: 15.23 GB

2026-04-14 11:52:20 - 策略 1: 使用 ModelScope CLI 下载
2026-04-14 11:52:25 - Downloading [model.safetensors]:   1%|█       | 1M/392M
...
2026-04-14 11:54:25 - Downloading [model.safetensors]: 100%|████████| 392M/392M
2026-04-14 11:54:25 - ModelScope CLI 下载成功

详细日志文件: /workspace/models/Qwen2.5-7B-Instruct/model_download.log
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MODEL_DIR` | `/workspace/models` | 默认模型保存目录 |
| `HF_ENDPOINT` | `https://hf-mirror.com` | HuggingFace 端点 |
| `HF_TOKEN` | - | HuggingFace 认证令牌 |

## 依赖安装

```bash
# ModelScope（必需）
pip install modelscope

# HuggingFace CLI（可选）
pip install huggingface_hub[cli]
```

## 常见问题

**Q: 下载速度慢？**
A: 默认使用 `hf-mirror.com` 镜像加速。也可指定 `--source modelscope` 使用国内源。

**Q: 私有模型无法下载？**
A: 设置 `HF_TOKEN` 环境变量或使用 `--token` 参数。

**Q: 如何查看下载进度？**
A: 查看日志文件 `{save_path}/model_download.txt`，建议只读取最后 15-20 行。

## 参考
modelscope CLI 下载参考：https://www.modelscope.cn/docs/models/download
HuggingFace CLI 下载参考: https://github.com/huggingface/skills/blob/main/skills/hugging-face-cli/SKILL.md
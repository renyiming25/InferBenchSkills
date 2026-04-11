---
name: huggingface-trending
description: 从 HuggingFace Hub 获取热门模型排行。当用户需要了解当前最流行的 AI 模型、为研究或项目寻找热门模型，或根据特定筛选条件（允许的组织、任务类型）获取模型流行度指标的快照时，可以使用此脚本。
---

# Hugging Face 热门模型

使用 Python 脚本从 Hugging Face Hub 获取热门模型排行前 10 名。

## 快速开始

```bash
# 设置镜像环境变量（解决网络不通问题）
export HF_ENDPOINT=https://hf-mirror.com

# 方法1: 使用 HF CLI（快速获取）
hf models ls --sort trending_score --limit 10

# 方法2: 使用 Python 脚本（完整过滤）
python3 ./skills/huggingface-trending/scripts/get_trending_models.py
```

## 自定义过滤查询

如需过滤结果（特定组织和任务类型），使用提供的脚本：

```bash
# 设置镜像环境变量
export HF_ENDPOINT=https://hf-mirror.com

# 运行过滤脚本（如果 CLI 执行不通，直接用此脚本）
python3 ./skills/huggingface-trending/scripts/get_trending_models.py
```

## 过滤规则

脚本按以下条件过滤模型：
- **允许的组织**: Qwen, zai-org, MiniMax, moonshotai, deepseek-ai, tencent, ByteDance-Seed, google
- **任务类型**:  Image-Text-to-Text, Text Generation
- **排除模式**: 结尾为 -gguf 等量化版本

## 命令参考

| 命令 | 说明 |
|------|------|
| `hf models ls --sort trending_score --limit 10` | 获取热门模型前 10 名（所有组织、所有任务） |
| `python3 scripts/get_trending_models.py` | 获取热门模型前 10 名（自定义过滤） |
| `hf models ls --sort trending_score --limit 20` | 获取热门模型前 20 名 |
| `hf models ls --filter <task> --sort trending_score --limit 10` | 按任务类型过滤（如 text-generation、image-generation） |

## 输出格式

命令返回模型列表，包含：
- **模型 ID**: 唯一标识符（如 `meta-llama/Llama-3.2-1B-Instruct`）
- **点赞数**: 模型获得的点赞数量
- **下载量**: 总下载次数

输出示例：
```
1. Qwen/Qwen2.5-7B-Instruct
2. zai-org/zai-LLM-70B
3. MiniMax/MiniMax-M2.1
```

## 常见用途

- **发现热门模型**: 查看当前流行的模型
- **研究参考**: 寻找前沿模型进行学习或构建应用
- **模型选型**: 基于社区热度选择模型
- **保持更新**: 快速了解当前模型生态

## 注意事项

- 需要安装 `hf` CLI 并完成认证
- 热门度基于社区互动（点赞 + 下载）
- 结果从 HuggingFace Hub 实时获取
- 自定义脚本提供额外的组织和任务类型过滤

## 故障排除

1. **网络不通问题**: 如果访问 Hugging Face 失败，设置镜像环境变量：
   ```bash
   export HF_ENDPOINT=https://hf-mirror.com
   ```

2. **CLI 执行不通**: 如果 `hf` CLI 命令失败，直接使用 Python 脚本：
   ```bash
   python3 ./skills/huggingface-trending/scripts/get_trending_models.py
   ```
   脚本已内置镜像端点支持，会自动通过 `https://hf-mirror.com` 获取数据

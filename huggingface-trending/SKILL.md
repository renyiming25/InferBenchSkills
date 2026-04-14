---
name: huggingface-trending
description: 从 HuggingFace Hub 获取热门模型排行。当用户需要了解当前最流行的 AI 模型、为研究或项目寻找热门模型，或根据特定筛选条件（允许的组织、任务类型）获取模型流行度指标的快照时，可以使用此脚本。
---

# HuggingFace 热门模型

使用 Python 脚本从 HuggingFace Hub 获取热门模型排行。

## 快速开始

```bash
# 获取热门模型前 10 名（默认）
python3 ./skills/huggingface-trending/scripts/get_trending_models.py

# 获取热门模型前 20 名
python3 ./skills/huggingface-trending/scripts/get_trending_models.py 20

# 只获取 Google 的热门模型
python3 ./skills/huggingface-trending/scripts/get_trending_models.py 10 --org google

# 获取多个组织的模型
python3 ./skills/huggingface-trending/scripts/get_trending_models.py 10 --org google,Qwen,deepseek-ai

# 只获取 text-generation 任务类型
python3 ./skills/huggingface-trending/scripts/get_trending_models.py 10 --task text-generation

# 组合使用：指定组织和任务类型
python3 ./skills/huggingface-trending/scripts/get_trending_models.py 10 --org google --task image-text-to-text,any-to-any
```

## 使用方式

```bash
python3 get_trending_models.py [N] [OPTIONS]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `N` | 返回的模型数量（正整数） | 10 |
| `--org ORGS` | 组织列表（逗号分隔） | 内置默认列表 |
| `--task TASKS` | 任务类型列表（逗号分隔） | image-text-to-text,text-generation,any-to-any |

## 默认过滤规则

脚本按以下条件过滤模型：
- **允许的组织**: Qwen, zai-org, MiniMaxAI, moonshotai, deepseek-ai, tencent, ByteDance-Seed, google
- **任务类型**: image-text-to-text, text-generation, any-to-any
- **排除模式**: 量化版本 (-gguf, -int8, -awq, -gptq, -nvfp4 等)

## 常用任务类型

| 任务类型 | 说明 |
|----------|------|
| `text-generation` | 文本生成 |
| `image-text-to-text` | 图文多模态 |
| `any-to-any` | 任意到任意模态 |
| `text-to-speech` | 文本转语音 |
| `image-generation` | 图像生成 |
| `automatic-speech-recognition` | 语音识别 |

## 输出格式

命令返回模型列表，包含：
- **模型 ID**: 唯一标识符（如 `Qwen/Qwen3.5-9B`）
- **点赞数**: 模型获得的点赞数量
- **下载量**: 总下载次数
- **任务类型**: pipeline_tag

输出示例：
```
======================================================================
🔥 HuggingFace 热门模型 Top 5 (筛选后)
======================================================================

筛选条件:
  • 组织: google
  • 任务: image-text-to-text, text-generation, any-to-any
  • 排除: 量化版本 (gguf, int8, awq, gptq, nvfp4 等)

----------------------------------------------------------------------

 1. google/gemma-4-31B-it
    👍 1,872  ⬇️ 2.6M  🏷️ image-text-to-text

 2. google/gemma-4-E4B-it
    👍 640  ⬇️ 1.5M  🏷️ any-to-any

...

======================================================================
共找到 8 个符合条件的模型
======================================================================
```

## 常见用途

- **发现热门模型**: 查看当前流行的模型
- **研究参考**: 寻找前沿模型进行学习或构建应用
- **模型选型**: 基于社区热度选择模型
- **保持更新**: 快速了解当前模型生态
- **特定组织模型**: 查看特定厂商（如 Google、Qwen）的热门模型

## 注意事项

- 热门度基于社区互动（点赞 + 下载）
- 结果从 HuggingFace Hub 实时获取
- 脚本已内置镜像端点支持，自动通过 `https://hf-mirror.com` 获取数据
- 如果符合条件的模型少于请求的数量，将返回所有符合条件的模型

## 故障排除

1. **网络不通问题**: 脚本已内置镜像端点，如仍无法访问，可手动设置：
   ```bash
   export HF_ENDPOINT=https://hf-mirror.com
   ```

2. **依赖缺失**: 确保已安装 huggingface_hub：
   ```bash
   pip install huggingface_hub
   ```
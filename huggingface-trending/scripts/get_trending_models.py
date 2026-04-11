#!/usr/bin/env python3
"""
Fetch top 10 trending models from Hugging Face Hub with custom filters.

Filters:
- Allowed organizations: Qwen, zai-org, MiniMax, moonshotai, deepseek-ai, tencent, ByteDance-Seed
- Task types: Image-Text-to-Text, Text Generation
- Excluded: Models ending with -FP8 or -GGUF
"""
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from huggingface_hub import list_models

allowed_orgs = {
    "Qwen",
    "zai-org",
    "MiniMax",
    "moonshotai",
    "deepseek-ai",
    "tencent",
    "ByteDance-Seed",
    "google"
}

exclude_suffixes = (
    "-int8",
    "-awq",
    "-gptq",
    "-gguf",
    "-4bit",
    "-8bit"
)

# 只保留这两个类别的模型：
allowed_tasks = {
    "image-text-to-text",
    "text-generation",
}

# list_models 返回的是一个 generator，这里先转成 list，方便后续多次遍历和切片
models = list(
    list_models(
        sort="trending_score",
        full=True,
        limit=100
    )
)

# 先过滤，再取前 10 个输出
filtered_models = []
for m in models:
    org = m.modelId.split("/")[0]
    if org not in allowed_orgs:
        continue

    # 进一步按任务类型过滤：只保留 Image-Text-to-Text / Text Generation
    pipeline_tag = getattr(m, "pipeline_tag", None)
    if pipeline_tag not in allowed_tasks:
        continue

    # 排除 -GGUF 结尾
    model_name = m.modelId.split("/")[1]
    if model_name.lower().endswith(exclude_suffixes):
        continue

    filtered_models.append(m)

for i, model in enumerate(filtered_models[:10], 1):
    print(f"{i}. {model.modelId}")

# InferBenchSkills

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

构建 **"HuggingFace 热门模型发现 → 下载上传 OSS 存储 → Benchmark 效果与性能验证 → 自测报告生成"** 的全流程 AI Skills 集合，支持 [Claude Code](https://claude.ai/code) 和 [OpenClaw](https://openclaw.com) 两种 AI Agent 框架。


## Skills 列表

| Skill | 说明 | 脚本 |
|-------|------|------|
| [huggingface-trending](huggingface-trending/) | 从 HuggingFace Hub 获取热门模型排行，支持按组织、任务类型筛选 | `scripts/get_trending_models.py` |
| [model-download](model-download/) | 从 ModelScope / HuggingFace 下载 AI 模型，支持多级下载策略、后台下载 | `scripts/download_model_skill.py` |
| [sglang-model-eval](sglang-model-eval/) | 基于 SGLang 框架运行基准测试（GPQA/MMLU/GSM8K 等）和性能测试 | `scripts/eval_model.py` |
| [sglang-benchmark-reporter](sglang-benchmark-reporter/) | 读取评估结果 JSON，生成单模型报告或多模型对比报告 | `scripts/generate_report.py` |
| [hf-trending-reminder](hf-trending-reminder/) | 定时获取热门模型并通过飞书机器人推送（9:00-21:00，每 2 小时） | cron 定时任务 |

### 安装 Skills

#### Claude Code、OpenClaw 安装

```bash
# 安装所有 skill
npx skills add https://github.com/renyiming25/InferBenchSkills.git

# 安装单个 skill（仅安装 model-download）
npx skills add https://github.com/renyiming25/InferBenchSkills.git --skill model-download
```
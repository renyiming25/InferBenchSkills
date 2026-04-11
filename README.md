# InferBenchSkills
构建“huggingface 热门模型发现 → 下载上传 oss 存储 →  benchmark 效果与性能验证 → 自测报告生成”的全流程 skills

## hf-trending-reminder
- 定时任务，每天上午 9:00 到晚上 8:00，每 2 小时获取一次 Hugging Face 热门模型并发送到飞书。


## huggingface-trending
- 从 HuggingFace Hub 获取热门模型排行。当用户需要了解当前最流行的 AI 模型、为研究或项目寻找热门模型，或根据特定筛选条件（允许的组织、任务类型）获取模型流行度指标的快照时，可以使用此脚本。

筛选条件：
- 允许的组织：Qwen、zai-org、MiniMax、moonshotai、deepseek-ai、腾讯、字节跳动-Seed
- 任务类型：图像到文本、文本生成
- 排除的模型：以 -FP8 或 -GGUF 结尾的模型


## model-download
- 从 ModelScope 或 HuggingFace 下载 AI 模型。支持多级下载策略：优先使用 ModelScope CLI，失败则尝试 HuggingFace CLI，最后使用 ModelScope Python SDK。支持后台下载、日志记录和下载完成后的简要总结。当用户需要下载模型时使用此 skill。


## sglang-model-eval
- SGLang 模型评估 Skill，用于自动化评估模型效果。支持准确性测试（GPQA、MMLU、GSM8K、HumanEval、HellaSwag）和性能测试（延迟、吞吐量）。

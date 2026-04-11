# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Claude Code skill that fetches top 10 trending models from Hugging Face Hub. It provides two methods:
1. HF CLI (`hf models ls --sort trending_score --limit 10`)
2. Python script with custom filters (`scripts/get_trending_models.py`)

## Running the Script

```bash
# The script has a built-in mirror endpoint for network issues
python3 scripts/get_trending_models.py
```

## Architecture

- **SKILL.md**: Skill definition with frontmatter (name, description) and usage documentation
- **scripts/get_trending_models.py**: Python script using `huggingface_hub.list_models()` API

The script filters models by:
- Organizations: Qwen, zai-org, MiniMax, moonshotai, deepseek-ai, tencent, ByteDance-Seed
- Task types: image-text-to-text, text-generation
- Excludes models ending with: -fp8, -int8, -awq, -gptq, -gguf, -4bit, -8bit

## Dependencies

- `huggingface_hub` Python package
- Optional: `hf` CLI (huggingface-cli) for quick queries

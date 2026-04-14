#!/usr/bin/env python3
"""
Fetch top N trending models from Hugging Face Hub with custom filters.

Usage:
    python3 get_trending_models.py [N] [OPTIONS]

Arguments:
    N  - Number of models to return (default: 10)

Options:
    --org ORGS      - Comma-separated list of organizations (default: built-in list)
    --task TASKS    - Comma-separated list of task types (default: image-text-to-text,text-generation,any-to-any)

Examples:
    python3 get_trending_models.py 10
    python3 get_trending_models.py 20 --org google
    python3 get_trending_models.py 10 --org google,Qwen,deepseek-ai
    python3 get_trending_models.py 10 --task text-generation
    python3 get_trending_models.py 10 --org google --task image-text-to-text,any-to-any

Filters:
- Excluded: Models ending with quantization suffixes (-gguf, -int8, -awq, etc.)
"""
import os
import sys
import argparse

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from huggingface_hub import list_models

# Default filter conditions
DEFAULT_ORGS = {
    "Qwen",
    "zai-org",
    "MiniMaxAI",
    "moonshotai",
    "deepseek-ai",
    "tencent",
    "ByteDance-Seed",
    "google"
}

DEFAULT_TASKS = {
    "image-text-to-text",
    "text-generation",
    "any-to-any"
}

EXCLUDE_SUFFIXES = (
    "-int8",
    "-awq",
    "-gptq",
    "-gguf",
    "-4bit",
    "-8bit",
    "-nvfp4",
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch top N trending models from Hugging Face Hub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            %(prog)s 10                          Top 10 with default filters
            %(prog)s 20 --org google             Top 20 from Google only
            %(prog)s 10 --org google,Qwen        Top 10 from Google and Qwen
            %(prog)s 10 --task text-generation   Top 10 for text-generation only
        """
    )
    parser.add_argument(
        "n",
        type=int,
        nargs="?",
        default=10,
        help="Number of models to return (default: 10)"
    )
    parser.add_argument(
        "--org",
        type=str,
        default=None,
        help="Comma-separated list of organizations (default: built-in list)"
    )
    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="Comma-separated list of task types (default: image-text-to-text,text-generation,any-to-any)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    top_n = args.n
    if top_n < 1:
        print("Error: N must be a positive integer")
        sys.exit(1)

    # Parse organizations
    if args.org:
        allowed_orgs = set(org.strip() for org in args.org.split(",") if org.strip())
    else:
        allowed_orgs = DEFAULT_ORGS

    # Parse task types
    if args.task:
        allowed_tasks = set(task.strip().lower() for task in args.task.split(",") if task.strip())
    else:
        allowed_tasks = DEFAULT_TASKS

    # Fetch models (get more than needed to account for filtering)
    fetch_limit = max(top_n * 5, 100)

    models = list(
        list_models(
            sort="trending_score",
            full=True,
            limit=fetch_limit
        )
    )

    # Apply filters
    filtered_models = []
    for m in models:
        org = m.modelId.split("/")[0]
        if org not in allowed_orgs:
            continue

        pipeline_tag = getattr(m, "pipeline_tag", None)
        if pipeline_tag not in allowed_tasks:
            continue

        model_name = m.modelId.split("/")[1]
        if model_name.lower().endswith(EXCLUDE_SUFFIXES):
            continue

        filtered_models.append(m)

    # Output header
    print("=" * 70)
    print(f"🔥 HuggingFace 热门模型 Top {top_n} (筛选后)")
    print("=" * 70)
    print()
    print("筛选条件:")
    print(f"  • 组织: {', '.join(sorted(allowed_orgs))}")
    print(f"  • 任务: {', '.join(sorted(allowed_tasks))}")
    print(f"  • 排除: 量化版本 (gguf, int8, awq, gptq, nvfp4 等)")
    print()
    print("-" * 70)
    print()

    # Output results
    for i, m in enumerate(filtered_models[:top_n], 1):
        likes = getattr(m, 'likes', 0) or 0
        downloads = getattr(m, 'downloads', 0) or 0
        pipeline = getattr(m, 'pipeline_tag', 'N/A') or 'N/A'

        # Format download count
        if downloads >= 1000000:
            dl_str = f"{downloads/1000000:.1f}M"
        elif downloads >= 1000:
            dl_str = f"{downloads/1000:.1f}K"
        else:
            dl_str = str(downloads)

        print(f"{i:2d}. {m.modelId}")
        print(f"    👍 {likes:,}  ⬇️ {dl_str}  🏷️ {pipeline}")
        print()

    # Output footer
    print("=" * 70)
    print(f"共找到 {len(filtered_models)} 个符合条件的模型")
    print("=" * 70)


if __name__ == "__main__":
    main()
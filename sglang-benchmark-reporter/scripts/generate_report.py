#!/usr/bin/env python3
"""
SGLang Benchmark Report Generator

读取 sglang-model-eval 的评估结果 JSON 文件，生成结构化报告。
支持单模型报告和多模型对比报告。
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


# 默认配置
DEFAULT_REPORT_DIR = "/workspace/eval_reports"
DEFAULT_OUTPUT_DIR = "/workspace/eval_reports"


def load_json_files(report_dir: str, model_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """加载所有 JSON 结果文件"""
    results = []
    report_path = Path(report_dir)

    if not report_path.exists():
        print(f"错误: 报告目录不存在: {report_dir}")
        return results

    json_files = sorted(report_path.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)

    for json_file in json_files:
        try:
            with open(json_file, "r") as f:
                data = json.load(f)

            # 添加文件路径信息
            data["_file_path"] = str(json_file)
            data["_file_mtime"] = datetime.fromtimestamp(json_file.stat().st_mtime)

            # 模型筛选
            if model_filter:
                model_name = data.get("model_name", "")
                if model_filter.lower() not in model_name.lower():
                    continue

            results.append(data)
        except Exception as e:
            print(f"警告: 无法加载 {json_file}: {e}")

    return results


def get_latest_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """获取每个模型的最新结果"""
    model_results: Dict[str, Dict[str, Any]] = {}

    for result in results:
        model_name = result.get("model_name", "unknown")
        eval_time = result.get("evaluation_time", "")

        if model_name not in model_results:
            model_results[model_name] = result
        else:
            existing_time = model_results[model_name].get("evaluation_time", "")
            if eval_time > existing_time:
                model_results[model_name] = result

    return list(model_results.values())


def format_accuracy(value: Any) -> str:
    """格式化准确率"""
    if value is None:
        return "-"
    if isinstance(value, float):
        if value <= 1.0:
            return f"{value:.2%}"
        return f"{value:.2f}%"
    return str(value)


def format_duration(seconds: Any) -> str:
    """格式化持续时间"""
    if seconds is None:
        return "-"
    if isinstance(seconds, (int, float)):
        return f"{seconds:.2f}s"
    return str(seconds)


def format_number(value: Any, decimals: int = 2) -> str:
    """格式化数字"""
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:.{decimals}f}"
    return str(value)


def generate_single_report(data: Dict[str, Any]) -> str:
    """生成单模型报告"""
    model_name = data.get("model_name", "Unknown")
    model_id = data.get("model_id", "-")
    eval_time = data.get("evaluation_time", "-")
    status = data.get("status", "unknown")
    total_duration = data.get("total_duration_seconds")

    env = data.get("environment", {})
    benchmarks = data.get("benchmarks", {})
    performance = data.get("performance", {})
    errors = data.get("errors", [])

    lines = []
    lines.append(f"# 模型评估报告: {model_name}")
    lines.append("")
    lines.append("## 基本信息")
    lines.append(f"- **模型路径**: {model_id}")
    lines.append(f"- **评估时间**: {eval_time}")
    lines.append(f"- **评估状态**: {status}")
    if total_duration:
        lines.append(f"- **总耗时**: {format_duration(total_duration)}")
    lines.append("")

    # 环境信息
    lines.append("## 环境信息")
    lines.append(f"- **GPU**: {env.get('gpu', '-')}")
    lines.append(f"- **SGLang 版本**: {env.get('sglang_version', '-')}")
    lines.append(f"- **TP Size**: {env.get('tp_size', '-')}")
    lines.append(f"- **端口**: {env.get('port', '-')}")
    lines.append("")

    # 基准测试结果
    if benchmarks:
        lines.append("## 基准测试结果")
        lines.append("")
        lines.append("| Benchmark | Accuracy | Samples | Duration |")
        lines.append("|-----------|----------|---------|----------|")

        benchmark_order = ["gpqa", "mmlu", "gsm8k", "humaneval", "hellaswag"]
        for bench_name in benchmark_order:
            if bench_name in benchmarks:
                bench_data = benchmarks[bench_name]
                accuracy = bench_data.get("accuracy")
                samples = bench_data.get("samples", "-")
                duration = bench_data.get("duration_seconds")

                lines.append(f"| {bench_name.upper()} | {format_accuracy(accuracy)} | {samples} | {format_duration(duration)} |")

        # 其他未排序的基准测试
        for bench_name, bench_data in benchmarks.items():
            if bench_name not in benchmark_order:
                accuracy = bench_data.get("accuracy")
                samples = bench_data.get("samples", "-")
                duration = bench_data.get("duration_seconds")
                lines.append(f"| {bench_name.upper()} | {format_accuracy(accuracy)} | {samples} | {format_duration(duration)} |")

        lines.append("")

    # 性能测试结果
    if performance:
        lines.append("## 性能测试结果")
        lines.append("")

        latency = performance.get("latency", {})
        throughput = performance.get("throughput", {})
        throughput_multi = performance.get("throughput_multi", {})

        if latency:
            lines.append("### 延迟测试")
            lines.append("")
            lines.append("| 指标 | 值 |")
            lines.append("|------|-----|")
            ttft = latency.get("ttft_ms")
            lines.append(f"| TTFT (首Token延迟) | {format_number(ttft)} ms |")
            lines.append(f"| 测试请求数 | {latency.get('num_prompts', '-')} |")
            lines.append(f"| 输入长度 | {latency.get('random_input_len', '-')} |")
            lines.append(f"| 输出长度 | {latency.get('random_output_len', '-')} |")
            lines.append("")

        if throughput:
            lines.append("### 吞吐量测试")
            lines.append("")
            lines.append("| 指标 | 值 |")
            lines.append("|------|-----|")
            lines.append(f"| 总吞吐量 | {format_number(throughput.get('total_throughput_tokens_per_sec'))} tokens/s |")
            lines.append(f"| 输入吞吐量 | {format_number(throughput.get('input_throughput_tokens_per_sec'))} tokens/s |")
            lines.append(f"| 输出吞吐量 | {format_number(throughput.get('output_throughput_tokens_per_sec'))} tokens/s |")
            lines.append(f"| QPS | {format_number(throughput.get('qps'))} |")
            lines.append(f"| 并发数 | {throughput.get('concurrency', '-')} |")
            lines.append(f"| 成功请求数 | {throughput.get('successful_requests', '-')} |")
            lines.append(f"| 平均E2E延迟 | {format_number(throughput.get('mean_e2e_latency_ms'))} ms |")
            lines.append("")

        if throughput_multi:
            lines.append("### 多并发吞吐量测试")
            lines.append("")
            lines.append("| 并发数 | 吞吐量 (tokens/s) | QPS | 平均延迟 (ms) |")
            lines.append("|--------|-------------------|-----|---------------|")
            for key, data in sorted(throughput_multi.items()):
                concurrency = data.get("concurrency", "-")
                throughput_val = format_number(data.get("total_throughput_tokens_per_sec"))
                qps = format_number(data.get("qps"))
                latency_val = format_number(data.get("mean_e2e_latency_ms"))
                lines.append(f"| {concurrency} | {throughput_val} | {qps} | {latency_val} |")
            lines.append("")

    # 错误信息
    if errors:
        lines.append("## 错误信息")
        lines.append("")
        for error in errors:
            lines.append(f"- {error}")
        lines.append("")

    return "\n".join(lines)


def generate_compare_report(results: List[Dict[str, Any]]) -> str:
    """生成多模型对比报告"""
    lines = []
    lines.append("# 模型评估对比报告")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().isoformat()}")
    lines.append(f"**模型数量**: {len(results)}")
    lines.append("")

    # 按 model_name 排序
    results = sorted(results, key=lambda x: x.get("model_name", ""))

    # 收集所有基准测试类型
    all_benchmarks = set()
    for result in results:
        all_benchmarks.update(result.get("benchmarks", {}).keys())

    benchmark_order = ["gpqa", "mmlu", "gsm8k", "humaneval", "hellaswag"]
    benchmark_list = [b for b in benchmark_order if b in all_benchmarks]
    benchmark_list.extend(sorted(all_benchmarks - set(benchmark_order)))

    # 基准测试对比表
    lines.append("## 基准测试对比")
    lines.append("")

    header = "| Model |" + " | ".join(b.upper() for b in benchmark_list) + " |"
    separator = "|-------|" + "|".join(["------" for _ in benchmark_list]) + "|"

    lines.append(header)
    lines.append(separator)

    for result in results:
        model_name = result.get("model_name", "Unknown")
        benchmarks = result.get("benchmarks", {})

        row = f"| {model_name} |"
        for bench_name in benchmark_list:
            bench_data = benchmarks.get(bench_name, {})
            accuracy = bench_data.get("accuracy")
            row += f" {format_accuracy(accuracy)} |"

        lines.append(row)

    lines.append("")

    # 性能对比表
    has_performance = any(r.get("performance") for r in results)
    if has_performance:
        lines.append("## 性能对比")
        lines.append("")
        lines.append("| Model | TTFT (ms) | Throughput (tokens/s) | QPS |")
        lines.append("|-------|-----------|----------------------|-----|")

        for result in results:
            model_name = result.get("model_name", "Unknown")
            perf = result.get("performance", {})
            latency = perf.get("latency", {})
            throughput = perf.get("throughput", {})

            ttft = format_number(latency.get("ttft_ms"))
            throughput_val = format_number(throughput.get("total_throughput_tokens_per_sec"))
            qps = format_number(throughput.get("qps"))

            lines.append(f"| {model_name} | {ttft} | {throughput_val} | {qps} |")

        lines.append("")

    # 详细信息
    lines.append("## 详细信息")
    lines.append("")

    for result in results:
        model_name = result.get("model_name", "Unknown")
        eval_time = result.get("evaluation_time", "-")
        status = result.get("status", "-")
        env = result.get("environment", {})

        lines.append(f"### {model_name}")
        lines.append(f"- 评估时间: {eval_time}")
        lines.append(f"- 状态: {status}")
        lines.append(f"- GPU: {env.get('gpu', '-')}")
        lines.append(f"- SGLang: {env.get('sglang_version', '-')}")
        lines.append("")

    return "\n".join(lines)


def generate_summary_report(results: List[Dict[str, Any]]) -> str:
    """生成汇总统计报告"""
    lines = []
    lines.append("# 评估结果汇总")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().isoformat()}")
    lines.append("")

    # 统计信息
    total_evals = len(results)
    success_evals = sum(1 for r in results if r.get("status") == "success")
    models = set(r.get("model_name", "Unknown") for r in results)

    lines.append("## 统计概览")
    lines.append("")
    lines.append(f"- **总评估次数**: {total_evals}")
    lines.append(f"- **成功评估**: {success_evals}")
    lines.append(f"- **失败评估**: {total_evals - success_evals}")
    lines.append(f"- **模型数量**: {len(models)}")
    lines.append("")

    # 模型列表
    lines.append("## 模型列表")
    lines.append("")
    for model in sorted(models):
        count = sum(1 for r in results if r.get("model_name") == model)
        lines.append(f"- {model} ({count} 次评估)")
    lines.append("")

    # 评估历史
    lines.append("## 最近评估")
    lines.append("")
    lines.append("| 时间 | 模型 | 状态 |")
    lines.append("|------|------|------|")

    sorted_results = sorted(results, key=lambda x: x.get("evaluation_time", ""), reverse=True)[:20]
    for result in sorted_results:
        eval_time = result.get("evaluation_time", "-")
        model_name = result.get("model_name", "-")
        status = result.get("status", "-")
        lines.append(f"| {eval_time} | {model_name} | {status} |")

    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="SGLang Benchmark Report Generator")
    parser.add_argument(
        "--report_dir",
        type=str,
        default=DEFAULT_REPORT_DIR,
        help=f"评估结果 JSON 文件目录 (默认: {DEFAULT_REPORT_DIR})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="筛选指定模型（支持模糊匹配）",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="生成多模型对比报告",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="生成汇总统计报告",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出文件路径",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["markdown", "json"],
        default="markdown",
        help="输出格式 (默认: markdown)",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="只使用每个模型的最新结果",
    )

    args = parser.parse_args()

    # 加载数据
    results = load_json_files(args.report_dir, args.model)

    if not results:
        print("未找到评估结果文件")
        return 1

    # 筛选最新结果
    if args.latest:
        results = get_latest_results(results)

    # 生成报告
    if args.summary:
        report = generate_summary_report(results)
    elif args.compare:
        report = generate_compare_report(results)
    elif len(results) == 1:
        report = generate_single_report(results[0])
    else:
        # 多个结果时默认生成对比报告
        report = generate_compare_report(results)

    # 输出
    if args.format == "json":
        output = json.dumps([r for r in results if "_file_path" not in r], indent=2, ensure_ascii=False, default=str)
    else:
        output = report

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(output)
        print(f"报告已保存: {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    exit(main())
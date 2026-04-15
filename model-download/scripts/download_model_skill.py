#!/usr/bin/env python3
"""
模型下载 Skill - 支持从 ModelScope 和 HuggingFace 下载模型

下载策略（按优先级）:
1. 使用 ModelScope CLI 下载
2. 如果失败，尝试使用 HuggingFace CLI 下载
3. 如果都失败，使用 Python 脚本从 ModelScope 下载

功能特性:
- 多级下载策略（ModelScope CLI -> HuggingFace CLI -> ModelScope Python）
- 支持指定下载源 (--source)
- 后台下载和日志记录
- 文件大小预估
- 智能进度显示（减少日志频率）
"""

import argparse
import os
import re
import sys
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set

try:
    from modelscope import snapshot_download as ms_snapshot_download
except ImportError:
    ms_snapshot_download = None

try:
    from huggingface_hub import snapshot_download as hf_snapshot_download
    from huggingface_hub import model_info as hf_model_info
except ImportError:
    hf_snapshot_download = None
    hf_model_info = None


# 常量定义
DEFAULT_MODEL_DIR = "/workspace/models"
LOG_FILE_NAME = "model_download.log"

# 进度日志控制
PROGRESS_PERCENT_INTERVAL = 20  # 每 20% 记录一次
PROGRESS_TIME_INTERVAL = 600    # 每 10 分钟记录一次


def sanitize_model_name(model_id: str) -> str:
    """
    提取模型名称（只取最后一部分，去掉组织名）
    例如: Qwen/Qwen2.5-7B-Instruct -> Qwen2.5-7B-Instruct
    """
    model_parts = model_id.split("/")
    model_name = model_parts[-1] if len(model_parts) > 1 else model_parts[0]
    # 保留字母数字、连字符和点号
    safe_name = "".join(c if c.isalnum() or c in ("-", ".") else "-" for c in model_name)
    return safe_name


def generate_save_path(model_id: str, save_path: Optional[str] = None) -> Path:
    """生成模型保存路径"""
    if save_path:
        return Path(save_path)

    safe_name = sanitize_model_name(model_id)
    default_path = os.environ.get("MODEL_DIR", DEFAULT_MODEL_DIR)
    return Path(default_path) / safe_name


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes >= 1e12:
        return f"{size_bytes / 1e12:.2f} TB"
    elif size_bytes >= 1e9:
        return f"{size_bytes / 1e9:.2f} GB"
    elif size_bytes >= 1e6:
        return f"{size_bytes / 1e6:.2f} MB"
    elif size_bytes >= 1e3:
        return f"{size_bytes / 1e3:.2f} KB"
    else:
        return f"{size_bytes} B"


def estimate_model_size(model_id: str, token: Optional[str] = None) -> Optional[int]:
    """预估模型大小（从 HuggingFace API 获取）"""
    if hf_model_info is None:
        return None

    try:
        info = hf_model_info(model_id, token=token)
        if hasattr(info, 'siblings') and info.siblings:
            total_size = sum(
                f.size for f in info.siblings
                if hasattr(f, 'size') and f.size
            )
            return total_size if total_size > 0 else None
    except Exception:
        pass
    return None


def write_log_header(log_file: Path, model_id: str, save_path: Path, estimated_size: Optional[int] = None) -> None:
    """写入日志文件头部信息"""
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("模型下载日志\n")
        f.write("=" * 60 + "\n")
        f.write(f"模型 ID: {model_id}\n")
        f.write(f"保存路径: {save_path}\n")
        if estimated_size:
            f.write(f"预估大小: {format_size(estimated_size)}\n")
        f.write(f"开始时间: {datetime.now().isoformat()}\n")
        f.write("\n")


def write_log_message(log_file: Path, message: str) -> None:
    """追加日志消息"""
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
            f.flush()
    except Exception:
        pass


def read_log_tail(log_file: Path, n: int = 15) -> str:
    """读取日志文件最后 n 行"""
    if not log_file.exists():
        return "日志文件不存在"

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 提取头部关键信息
        header_lines = []
        for line in lines[:10]:
            line = line.strip()
            if line and ("模型 ID:" in line or "保存路径:" in line or
                         "预估大小:" in line or "开始时间:" in line):
                header_lines.append(line)

        # 获取最后 n 行
        tail_lines = [line.rstrip() for line in lines[-n:] if line.strip()]

        return "\n".join(header_lines + [""] + tail_lines)
    except Exception as e:
        return f"读取日志失败: {e}"


class ProgressFilter:
    """
    进度日志过滤器 - 减少日志频率

    规则：
    - 进度更新：每 5% 或每 60 秒记录一次
    - 关键信息：始终记录（开始、完成、错误等）
    """

    def __init__(self, percent_interval: int = 5, time_interval: int = 60):
        self.percent_interval = percent_interval
        self.time_interval = time_interval
        self.last_percent: Dict[str, int] = {}  # file -> last recorded percent
        self.last_time: Dict[str, float] = {}   # file -> last recorded timestamp

    def should_log(self, line: str) -> bool:
        """判断是否应该记录此行日志"""

        # 始终记录非进度行
        if not self._is_progress_line(line):
            return True

        # 解析进度信息
        file_name, percent = self._parse_progress(line)
        if file_name is None or percent is None:
            return True

        current_time = time.time()

        # 检查是否满足记录条件
        last_percent = self.last_percent.get(file_name, -1)
        last_time = self.last_time.get(file_name, 0)

        # 条件1: 进度变化超过阈值
        percent_changed = (percent - last_percent) >= self.percent_interval

        # 条件2: 时间间隔超过阈值
        time_elapsed = (current_time - last_time) >= self.time_interval

        # 条件3: 进度为 100%（完成）
        is_complete = percent >= 100

        if percent_changed or time_elapsed or is_complete:
            self.last_percent[file_name] = percent
            self.last_time[file_name] = current_time
            return True

        return False

    def _is_progress_line(self, line: str) -> bool:
        """判断是否为进度更新行"""
        return "Downloading" in line and "%" in line

    def _parse_progress(self, line: str) -> Tuple[Optional[str], Optional[int]]:
        """解析进度行，提取文件名和百分比"""
        # 匹配格式: Downloading [filename]: XX%|...
        match = re.search(r'Downloading \[([^\]]+)\]:\s*(\d+)%', line)
        if match:
            return match.group(1), int(match.group(2))
        return None, None


def run_command(cmd: List[str], log_file: Path, timeout: Optional[int] = None) -> Tuple[bool, str]:
    """
    运行命令并记录日志（带进度过滤）

    Returns:
        (是否成功, 错误信息)
    """
    try:
        write_log_message(log_file, f"执行命令: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # 进度过滤器
        progress_filter = ProgressFilter(
            percent_interval=PROGRESS_PERCENT_INTERVAL,
            time_interval=PROGRESS_TIME_INTERVAL
        )

        # 实时写入日志（带过滤）
        output_lines = []
        for line in process.stdout:
            line = line.rstrip()
            if line:
                # 应用进度过滤
                if progress_filter.should_log(line):
                    write_log_message(log_file, line)
                output_lines.append(line)

        process.wait(timeout=timeout)

        if process.returncode == 0:
            write_log_message(log_file, "命令执行成功")
            return True, ""
        else:
            error_msg = f"命令执行失败，退出码: {process.returncode}"
            write_log_message(log_file, error_msg)
            return False, error_msg

    except subprocess.TimeoutExpired:
        process.kill()
        error_msg = "命令执行超时"
        write_log_message(log_file, error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"执行命令时出错: {str(e)}"
        write_log_message(log_file, error_msg)
        return False, error_msg


def download_with_modelscope_cli(model_id: str, save_path: Path, log_file: Path) -> Tuple[bool, str]:
    """使用 ModelScope CLI 下载模型"""
    write_log_message(log_file, "尝试使用 ModelScope CLI 下载...")

    cmd = [
        "modelscope",
        "download",
        "--model", model_id,
        "--local_dir", str(save_path)
    ]

    success, error = run_command(cmd, log_file, timeout=7200)  # 2小时超时

    if success:
        if save_path.exists() and any(save_path.iterdir()):
            write_log_message(log_file, "ModelScope CLI 下载成功")
            return True, ""
        else:
            error_msg = "ModelScope CLI 下载完成但目录为空"
            write_log_message(log_file, error_msg)
            return False, error_msg

    return False, error


def download_with_huggingface_cli(model_id: str, save_path: Path, log_file: Path, token: Optional[str] = None) -> Tuple[bool, str]:
    """使用 HuggingFace CLI 下载模型"""
    write_log_message(log_file, "尝试使用 HuggingFace CLI 下载...")

    env = os.environ.copy()
    if "HF_ENDPOINT" not in env:
        env["HF_ENDPOINT"] = "https://hf-mirror.com"
        write_log_message(log_file, f"设置 HF_ENDPOINT={env['HF_ENDPOINT']}")

    cmd = [
        "huggingface-cli",
        "download",
        "--resume-download",
        model_id,
        "--local-dir", str(save_path),
        "--local-dir-use-symlinks", "False"
    ]

    if token:
        cmd.extend(["--token", token])
        write_log_message(log_file, "使用提供的 token 进行认证")

    success, error = run_command(cmd, log_file, timeout=7200)  # 2小时超时

    if success:
        if save_path.exists() and any(save_path.iterdir()):
            write_log_message(log_file, "HuggingFace CLI 下载成功")
            return True, ""
        else:
            error_msg = "HuggingFace CLI 下载完成但目录为空"
            write_log_message(log_file, error_msg)
            return False, error_msg

    return False, error


def download_with_modelscope_python(model_id: str, save_path: Path, log_file: Path) -> Tuple[bool, str]:
    """使用 Python 脚本从 ModelScope 下载模型"""
    write_log_message(log_file, "尝试使用 ModelScope Python SDK 下载...")

    if ms_snapshot_download is None:
        error_msg = "ModelScope Python SDK 未安装，请运行: pip install modelscope"
        write_log_message(log_file, error_msg)
        return False, error_msg

    try:
        write_log_message(log_file, f"开始下载模型 {model_id} 到 {save_path}")

        save_path.mkdir(parents=True, exist_ok=True)

        ms_snapshot_download(
            model_id=model_id,
            local_dir=str(save_path)
        )

        if save_path.exists() and any(save_path.iterdir()):
            write_log_message(log_file, "ModelScope Python SDK 下载成功")
            return True, ""
        else:
            error_msg = "ModelScope Python SDK 下载完成但目录为空"
            write_log_message(log_file, error_msg)
            return False, error_msg

    except Exception as e:
        error_msg = f"ModelScope Python SDK 下载失败: {str(e)}"
        write_log_message(log_file, error_msg)
        return False, error_msg


def download_model(
    model_id: str,
    save_path: Optional[str] = None,
    token: Optional[str] = None,
    background: bool = True,
    source: str = "auto"
) -> Dict:
    """
    下载模型（多级策略）

    Args:
        model_id: 模型标识符（ModelScope 或 HuggingFace 格式）
        save_path: 本地保存目录路径
        token: HuggingFace 认证令牌（可选）
        background: 是否后台下载（默认 True）
        source: 下载源 (auto, modelscope, huggingface)

    Returns:
        dict: 包含状态、路径和消息的下载结果
    """
    result = {
        "status": "pending",
        "model_id": model_id,
        "save_path": None,
        "method": None,
        "estimated_size": None,
        "messages": [],
        "errors": [],
        "log_file": None,
        "summary": None
    }

    try:
        # 生成保存路径
        save_path_obj = generate_save_path(model_id, save_path)
        result["save_path"] = str(save_path_obj)

        # 预估模型大小
        estimated_size = estimate_model_size(model_id, token)
        if estimated_size:
            result["estimated_size"] = format_size(estimated_size)
            print(f"预估模型大小: {result['estimated_size']}")

        # 创建目标目录
        save_path_obj.mkdir(parents=True, exist_ok=True)

        # 初始化日志文件
        log_file = save_path_obj / LOG_FILE_NAME
        result["log_file"] = str(log_file)
        write_log_header(log_file, model_id, save_path_obj, estimated_size)

        result["messages"].append(f"开始下载模型 {model_id} 到 {save_path_obj}")

        # 定义下载函数（在后台线程中运行）
        def download_task():
            nonlocal result

            # 根据指定的下载源决定策略顺序
            if source == "modelscope":
                strategies = [
                    ("ModelScope CLI", lambda: download_with_modelscope_cli(model_id, save_path_obj, log_file)),
                    ("ModelScope Python SDK", lambda: download_with_modelscope_python(model_id, save_path_obj, log_file)),
                ]
            elif source == "huggingface":
                strategies = [
                    ("HuggingFace CLI", lambda: download_with_huggingface_cli(model_id, save_path_obj, log_file, token)),
                ]
            else:  # auto
                strategies = [
                    ("ModelScope CLI", lambda: download_with_modelscope_cli(model_id, save_path_obj, log_file)),
                    ("HuggingFace CLI", lambda: download_with_huggingface_cli(model_id, save_path_obj, log_file, token)),
                    ("ModelScope Python SDK", lambda: download_with_modelscope_python(model_id, save_path_obj, log_file)),
                ]

            for i, (strategy_name, download_func) in enumerate(strategies, 1):
                write_log_message(log_file, "=" * 60)
                write_log_message(log_file, f"策略 {i}: 使用 {strategy_name} 下载")

                success, error = download_func()

                if success:
                    result["status"] = "success"
                    result["method"] = strategy_name.lower().replace(" ", "-")
                    result["messages"].append(f"✓ 使用 {strategy_name} 下载成功")
                    write_log_message(log_file, "=" * 60)
                    write_log_message(log_file, f"下载状态: 成功 (方法: {strategy_name})")
                    return

                result["errors"].append(f"{strategy_name} 失败: {error}")

            # 所有策略都失败
            result["status"] = "error"
            write_log_message(log_file, "=" * 60)
            write_log_message(log_file, "下载状态: 失败 - 所有策略均失败")

            result["summary"] = read_log_tail(log_file)

        if background:
            result["messages"].append("模型正在后台下载中...")
            thread = threading.Thread(target=download_task, daemon=False)
            thread.start()
            result["thread"] = thread
            result["messages"].append("下载任务已启动，请稍后查看日志文件获取进度")
        else:
            download_task()
            result["summary"] = read_log_tail(log_file)

    except Exception as e:
        result["status"] = "error"
        error_msg = str(e)
        result["errors"].append(error_msg)
        result["messages"].append(f"下载失败: {error_msg}")

        if "log_file" in result and result["log_file"]:
            write_log_message(Path(result["log_file"]), f"错误: {error_msg}")

    return result


def wait_for_download(result: Dict, timeout: Optional[int] = None) -> Dict:
    """等待后台下载完成"""
    if "thread" not in result:
        return result

    thread = result["thread"]
    thread.join(timeout=timeout)

    if thread.is_alive():
        result["messages"].append("下载仍在进行中（可能超时）")
    else:
        result["messages"].append("下载已完成")
        result["summary"] = read_log_tail(Path(result["log_file"]))

    return result


def print_results(result: Dict) -> None:
    """打印下载结果"""
    print("\n" + "=" * 60)
    print("模型下载结果")
    print("=" * 60)
    print(f"模型 ID: {result['model_id']}")
    print(f"保存路径: {result['save_path']}")

    if result.get('estimated_size'):
        print(f"预估大小: {result['estimated_size']}")

    print(f"状态: {result['status'].upper()}")

    if result.get('method'):
        print(f"下载方法: {result['method']}")
    print()

    if result['messages']:
        print("消息:")
        for msg in result['messages']:
            print(f"  {msg}")
        print()

    if result['errors']:
        print("错误:")
        for error in result['errors']:
            print(f"  ✗ {error}")
        print()

    if result.get('summary'):
        print("下载日志摘要:")
        print(result['summary'])
        print()

    if result.get('log_file'):
        print(f"详细日志文件: {result['log_file']}")


def main():
    """主函数：解析命令行参数并执行下载"""
    parser = argparse.ArgumentParser(
        description="从 ModelScope 或 HuggingFace 下载 AI 模型",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 下载模型（后台下载）
  %(prog)s --model_id Qwen/Qwen2.5-7B-Instruct

  # 指定下载源
  %(prog)s --model_id Qwen/Qwen2.5-7B-Instruct --source huggingface

  # 下载到指定路径
  %(prog)s --model_id Qwen/Qwen2.5-7B-Instruct --save_path ./my_models

  # 同步下载（等待完成）
  %(prog)s --model_id Qwen/Qwen2.5-7B-Instruct --no-background

环境变量:
  MODEL_DIR: 默认模型保存目录（默认: /workspace/models）
  HF_ENDPOINT: HuggingFace 端点（默认: https://hf-mirror.com）
  HF_TOKEN: HuggingFace 认证令牌
        """
    )

    parser.add_argument(
        "--model_id",
        required=True,
        help="模型标识符（例如: Qwen/Qwen2.5-7B-Instruct）"
    )

    parser.add_argument(
        "--save_path",
        help="本地保存目录路径（未提供则自动生成）"
    )

    parser.add_argument(
        "--token",
        help="HuggingFace 认证令牌（也可通过 HF_TOKEN 环境变量设置）"
    )

    parser.add_argument(
        "--source",
        choices=["auto", "modelscope", "huggingface"],
        default="auto",
        help="下载源: auto(自动尝试), modelscope, huggingface (默认: auto)"
    )

    parser.add_argument(
        "--no-background",
        action="store_true",
        help="同步下载（等待完成），默认是后台下载"
    )

    parser.add_argument(
        "--wait-timeout",
        type=int,
        help="等待后台下载完成的超时时间（秒），默认不等待"
    )

    args = parser.parse_args()

    # 获取 token（优先使用参数，其次环境变量）
    token = args.token or os.environ.get("HF_TOKEN")

    # 下载模型
    result = download_model(
        model_id=args.model_id,
        save_path=args.save_path,
        token=token,
        background=not args.no_background,
        source=args.source
    )

    # 如果是后台下载且指定了等待超时，则等待
    if not args.no_background and args.wait_timeout:
        result = wait_for_download(result, timeout=args.wait_timeout)

    # 打印结果
    print_results(result)

    # 返回退出码
    sys.exit(0 if result['status'] == 'success' else 1)


if __name__ == "__main__":
    main()
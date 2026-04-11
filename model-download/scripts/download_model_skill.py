#!/usr/bin/env python3
"""
模型下载 Skill - 支持从 ModelScope 和 HuggingFace 下载模型

下载策略（按优先级）:
1. 使用 ModelScope CLI 下载
2. 如果失败，尝试使用 HuggingFace CLI 下载
3. 如果都失败，使用 Python 脚本从 ModelScope 下载

功能特性:
- 多级下载策略（ModelScope CLI -> HuggingFace CLI -> ModelScope Python）
- 后台下载和日志记录
- 下载完成后返回简要总结
"""

import argparse
import os
import sys
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    from modelscope import snapshot_download as ms_snapshot_download
except ImportError:
    ms_snapshot_download = None

try:
    from huggingface_hub import snapshot_download as hf_snapshot_download
except ImportError:
    hf_snapshot_download = None


# 常量定义
DEFAULT_MODEL_DIR = "/workspace/models"
LOG_FILE_NAME = "download_log.txt"


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


def write_log_header(log_file: Path, model_id: str, save_path: Path) -> None:
    """写入日志文件头部信息"""
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("模型下载日志\n")
        f.write("=" * 60 + "\n")
        f.write(f"模型 ID: {model_id}\n")
        f.write(f"保存路径: {save_path}\n")
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


def read_log_summary(log_file: Path) -> str:
    """读取日志文件并生成简要总结"""
    if not log_file.exists():
        return "日志文件不存在"
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # 提取关键信息
        summary_lines = []
        for line in lines:
            line = line.strip()
            if "模型 ID:" in line or "保存路径:" in line:
                summary_lines.append(line)
            elif "开始时间:" in line:
                summary_lines.append(line)
            elif "下载状态:" in line or "错误:" in line:
                summary_lines.append(line)
        
        # 获取最后几行关键信息
        if len(lines) > 10:
            summary_lines.extend(lines[-10:])
        
        return "\n".join(summary_lines)
    except Exception as e:
        return f"读取日志失败: {e}"


def run_command(cmd: List[str], log_file: Path, timeout: Optional[int] = None) -> Tuple[bool, str]:
    """
    运行命令并记录日志
    
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
        
        # 实时写入日志
        output_lines = []
        for line in process.stdout:
            line = line.rstrip()
            if line:
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
    
    # 构建命令: modelscope download --model Qwen/Qwen2.5-7B-Instruct --local_dir ./Qwen2.5-7B-Instruct
    cmd = [
        "modelscope",
        "download",
        "--model", model_id,
        "--local_dir", str(save_path)
    ]
    
    success, error = run_command(cmd, log_file, timeout=3600)  # 1小时超时
    
    if success:
        # 检查下载是否真的成功（检查目录中是否有文件）
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
    
    # 设置 HF_ENDPOINT 环境变量（如果未设置）
    env = os.environ.copy()
    if "HF_ENDPOINT" not in env:
        env["HF_ENDPOINT"] = "https://hf-mirror.com"
        write_log_message(log_file, f"设置 HF_ENDPOINT={env['HF_ENDPOINT']}")
    
    # 构建命令: huggingface-cli download --resume-download Qwen/Qwen3-Coder-Next --local-dir ./ --local-dir-use-symlinks False --token xxx
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
    
    success, error = run_command(cmd, log_file, timeout=3600)  # 1小时超时
    
    if success:
        # 检查下载是否真的成功
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
        
        # 确保目录存在
        save_path.mkdir(parents=True, exist_ok=True)
        
        # 使用 ModelScope SDK 下载
        # ModelScope 的 snapshot_download 支持 local_dir 参数
        ms_snapshot_download(
            model_id=model_id,
            local_dir=str(save_path)
        )
        
        # 检查下载是否成功
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
    background: bool = True
) -> Dict:
    """
    下载模型（多级策略）
    
    Args:
        model_id: 模型标识符（ModelScope 或 HuggingFace 格式）
        save_path: 本地保存目录路径
        token: HuggingFace 认证令牌（可选）
        background: 是否后台下载（默认 True）
    
    Returns:
        dict: 包含状态、路径和消息的下载结果
    """
    result = {
        "status": "pending",
        "model_id": model_id,
        "save_path": None,
        "method": None,
        "messages": [],
        "errors": [],
        "log_file": None,
        "summary": None
    }
    
    try:
        # 生成保存路径
        save_path_obj = generate_save_path(model_id, save_path)
        result["save_path"] = str(save_path_obj)
        
        # 创建目标目录
        save_path_obj.mkdir(parents=True, exist_ok=True)
        
        # 初始化日志文件
        log_file = save_path_obj / LOG_FILE_NAME
        result["log_file"] = str(log_file)
        write_log_header(log_file, model_id, save_path_obj)
        
        result["messages"].append(f"开始下载模型 {model_id} 到 {save_path_obj}")
        
        # 定义下载函数（在后台线程中运行）
        def download_task():
            nonlocal result
            
            # 策略1: 尝试 ModelScope CLI
            write_log_message(log_file, "=" * 60)
            write_log_message(log_file, "策略 1: 使用 ModelScope CLI 下载")
            success, error = download_with_modelscope_cli(model_id, save_path_obj, log_file)
            
            if success:
                result["status"] = "success"
                result["method"] = "modelscope-cli"
                result["messages"].append("✓ 使用 ModelScope CLI 下载成功")
                write_log_message(log_file, "=" * 60)
                write_log_message(log_file, f"下载状态: 成功 (方法: ModelScope CLI)")
                return
            
            result["errors"].append(f"ModelScope CLI 失败: {error}")
            
            # 策略2: 尝试 HuggingFace CLI
            write_log_message(log_file, "=" * 60)
            write_log_message(log_file, "策略 2: 使用 HuggingFace CLI 下载")
            success, error = download_with_huggingface_cli(model_id, save_path_obj, log_file, token)
            
            if success:
                result["status"] = "success"
                result["method"] = "huggingface-cli"
                result["messages"].append("✓ 使用 HuggingFace CLI 下载成功")
                write_log_message(log_file, "=" * 60)
                write_log_message(log_file, f"下载状态: 成功 (方法: HuggingFace CLI)")
                return
            
            result["errors"].append(f"HuggingFace CLI 失败: {error}")
            
            # 策略3: 尝试 ModelScope Python SDK
            write_log_message(log_file, "=" * 60)
            write_log_message(log_file, "策略 3: 使用 ModelScope Python SDK 下载")
            success, error = download_with_modelscope_python(model_id, save_path_obj, log_file)
            
            if success:
                result["status"] = "success"
                result["method"] = "modelscope-python"
                result["messages"].append("✓ 使用 ModelScope Python SDK 下载成功")
                write_log_message(log_file, "=" * 60)
                write_log_message(log_file, f"下载状态: 成功 (方法: ModelScope Python SDK)")
                return
            
            result["status"] = "error"
            result["errors"].append(f"ModelScope Python SDK 失败: {error}")
            write_log_message(log_file, "=" * 60)
            write_log_message(log_file, f"下载状态: 失败 - 所有策略均失败")
            
            # 生成最终总结
            result["summary"] = read_log_summary(log_file)
        
        if background:
            # 后台下载
            result["messages"].append("模型正在后台下载中...")
            thread = threading.Thread(target=download_task, daemon=False)
            thread.start()
            result["thread"] = thread
            result["messages"].append("下载任务已启动，请稍后查看日志文件获取进度")
        else:
            # 同步下载
            download_task()
            result["summary"] = read_log_summary(log_file)
    
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
        result["summary"] = read_log_summary(Path(result["log_file"]))
    
    return result


def print_results(result: Dict) -> None:
    """打印下载结果"""
    print("\n" + "=" * 60)
    print("模型下载结果")
    print("=" * 60)
    print(f"模型 ID: {result['model_id']}")
    print(f"保存路径: {result['save_path']}")
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

  # 下载到指定路径
  %(prog)s --model_id Qwen/Qwen2.5-7B-Instruct --save_path ./my_models

  # 同步下载（等待完成）
  %(prog)s --model_id Qwen/Qwen2.5-7B-Instruct --no-background

  # 使用 HuggingFace token
  %(prog)s --model_id username/private-model --token YOUR_HF_TOKEN

环境变量:
  MODEL_DIR: 默认模型保存目录（默认: /workspace/models）
  HF_ENDPOINT: HuggingFace 端点（默认: https://hf-mirror.com）
  HF_TOKEN: HuggingFace 认证令牌

目录规则:
  模型 ID: Qwen/Qwen2.5-7B-Instruct
  本地目录: /workspace/models/Qwen2.5-7B-Instruct
  (只取模型名的最后一部分，去掉组织名)
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
        background=not args.no_background
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


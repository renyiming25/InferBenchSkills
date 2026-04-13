#!/usr/bin/env python3
"""
SGLang 模型评估脚本

自动化评估模型效果，支持准确性测试和性能测试，生成结构化报告。
全程日志记录到 model_eval_<日期>.log 文件。
"""

import argparse
import json
import logging
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


# 默认配置
DEFAULT_PORT = 30000
DEFAULT_TP = 1
DEFAULT_MEM_FRACTION = 0.8
DEFAULT_MAX_TOKENS = 32768
DEFAULT_REPORT_DIR = "/workspace/eval_reports"
DEFAULT_LOG_DIR = "/workspace/eval_logs"
DEFAULT_MODEL_DIR = "/workspace/models"

# 基准测试默认样本数
DEFAULT_NUM_EXAMPLES = {
    "gpqa": 198,
    "mmlu": 1000,
    "gsm8k": 200,
    "humaneval": 164,
    "hellaswag": 200,
}

# 性能测试默认配置
PERF_TEST_CONFIG = {
    "latency": {"num_prompts": 10, "concurrency": 1},
    "throughput": {"num_prompts": 500, "concurrency": 100},
}


class Logger:
    """评估日志管理器"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if Logger._initialized:
            return
        Logger._initialized = True

        self.log_dir = Path(DEFAULT_LOG_DIR)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 日志文件名: model_eval_<日期>.log
        self.log_file = self.log_dir / f"model_eval_{datetime.now().strftime('%Y%m%d')}.log"

        # 配置日志格式
        self.logger = logging.getLogger("model_eval")
        self.logger.setLevel(logging.DEBUG)

        # 清除已有的 handlers
        self.logger.handlers.clear()

        # 文件处理器 - 记录所有级别
        file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # 控制台处理器 - 只显示 INFO 及以上
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def info(self, msg: str):
        self.logger.info(msg)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def log_command(self, cmd: List[str]):
        """记录执行的命令"""
        cmd_str = " ".join(cmd)
        self.logger.debug(f"执行命令: {cmd_str}")

    def log_output(self, output: str, max_len: int = 2000):
        """记录命令输出"""
        if output:
            # 截断过长的输出
            if len(output) > max_len:
                output = output[:max_len] + "\n... (输出已截断)"
            for line in output.strip().split("\n"):
                self.logger.debug(f"  {line}")

    def log_section(self, title: str):
        """记录章节标题"""
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info(f"  {title}")
        self.logger.info("=" * 60)

    def get_log_path(self) -> str:
        return str(self.log_file)


# 全局日志实例
log = Logger()


class ModelDownloader:
    """模型下载器 - 从 ModelScope 下载模型"""

    def __init__(self, model_dir: str = DEFAULT_MODEL_DIR):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def resolve_model_path(self, model_input: str) -> str:
        """
        解析模型路径

        优先级:
        1. 如果是绝对路径且存在，直接返回
        2. 如果是 HuggingFace/ModelScope ID 格式 (org/model)，检查本地是否存在
        3. 如果是模型名称 (如 Qwen3.5-0.8B)，在默认目录下查找
        4. 如果都不存在，自动从 ModelScope 下载

        Args:
            model_input: 模型路径、ID 或名称

        Returns:
            本地模型路径
        """
        model_input = model_input.strip()

        # 1. 绝对路径
        if model_input.startswith("/") and Path(model_input).exists():
            log.info(f"[模型] 使用本地路径: {model_input}")
            return model_input

        # 2. HuggingFace/ModelScope ID 格式 (如 Qwen/Qwen2.5-7B-Instruct)
        if "/" in model_input:
            org, model_name = model_input.split("/", 1)
            local_path = self.model_dir / model_name

            if local_path.exists() and self._is_valid_model_dir(local_path):
                log.info(f"[模型] 本地已存在: {local_path}")
                return str(local_path)

            # 需要下载
            return self._download_model(model_input, local_path)

        # 3. 模型名称 (如 Qwen3.5-0.8B)
        local_path = self.model_dir / model_input

        if local_path.exists() and self._is_valid_model_dir(local_path):
            log.info(f"[模型] 本地已存在: {local_path}")
            return str(local_path)

        # 4. 尝试常见的组织名称前缀下载
        # 常见组织: Qwen, deepseek-ai, meta-llama 等
        common_orgs = ["Qwen", "deepseek-ai", "meta-llama", "mistralai", "google"]

        for org in common_orgs:
            model_id = f"{org}/{model_input}"
            log.debug(f"[模型] 尝试从 {model_id} 下载...")
            try:
                return self._download_model(model_id, local_path)
            except Exception as e:
                log.debug(f"[模型] {model_id} 下载失败: {e}")
                continue

        raise ValueError(f"无法找到或下载模型: {model_input}")

    def _is_valid_model_dir(self, path: Path) -> bool:
        """检查是否是有效的模型目录"""
        if not path.is_dir():
            return False

        # 检查是否存在模型文件
        model_files = list(path.glob("*.json")) + list(path.glob("*.safetensors")) + list(path.glob("*.bin"))
        return len(model_files) > 0

    def _download_model(self, model_id: str, local_path: Path) -> str:
        """从 ModelScope 下载模型"""
        log.info(f"[模型] 从 ModelScope 下载: {model_id}")
        log.info(f"[模型] 保存到: {local_path}")

        # 使用 ModelScope CLI 下载
        cmd = [
            "modelscope", "download",
            "--model", model_id,
            "--local_dir", str(local_path),
        ]

        log.log_command(cmd)
        log.info("[模型] 下载中，请耐心等待...")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=7200  # 2小时超时
            )

            if result.returncode == 0:
                log.info(f"[模型] 下载完成: {local_path}")
                return str(local_path)
            else:
                error_msg = result.stderr or result.stdout
                log.error(f"[模型] ModelScope CLI 下载失败: {error_msg}")

                # 尝试使用 Python SDK
                return self._download_with_sdk(model_id, local_path)

        except subprocess.TimeoutExpired:
            log.error("[模型] 下载超时")
            raise RuntimeError("模型下载超时")
        except FileNotFoundError:
            log.warning("[模型] ModelScope CLI 未安装，尝试使用 Python SDK")
            return self._download_with_sdk(model_id, local_path)

    def _download_with_sdk(self, model_id: str, local_path: Path) -> str:
        """使用 ModelScope Python SDK 下载"""
        try:
            from modelscope import snapshot_download

            log.info(f"[模型] 使用 ModelScope SDK 下载: {model_id}")
            snapshot_download(model_id=model_id, local_dir=str(local_path))
            log.info(f"[模型] 下载完成: {local_path}")
            return str(local_path)

        except ImportError:
            log.error("[模型] ModelScope SDK 未安装，请运行: pip install modelscope")
            raise RuntimeError("ModelScope SDK 未安装")
        except Exception as e:
            log.error(f"[模型] SDK 下载失败: {e}")
            raise


class SGLangServer:
    """SGLang 服务器管理"""

    def __init__(self, model_path: str, port: int, tp: int, mem_fraction: float):
        self.model_path = model_path
        self.port = port
        self.tp = tp
        self.mem_fraction = mem_fraction
        self.process = None
        self.server_log_file = None

    def start(self, timeout: int = 300) -> bool:
        """启动服务器并等待就绪"""
        log.info(f"[SGLang] 启动服务器: {self.model_path}")

        # 启动命令
        cmd = [
            "python3", "-m", "sglang.launch_server",
            "--model-path", self.model_path,
            "--port", str(self.port),
            "--tp", str(self.tp),
            "--mem-fraction-static", str(self.mem_fraction),
        ]
        log.log_command(cmd)

        # 创建服务器日志文件
        log_dir = Path(DEFAULT_LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        self.server_log_file = log_dir / f"sglang_server_{self.port}.log"
        log.debug(f"服务器日志: {self.server_log_file}")

        # 启动进程
        with open(self.server_log_file, "w") as f:
            self.process = subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )

        log.info(f"[SGLang] 等待服务器就绪 (最长 {timeout}s)...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                import urllib.request
                urllib.request.urlopen(f"http://localhost:{self.port}/health", timeout=5)
                log.info(f"[SGLang] 服务器已就绪 (PID: {self.process.pid})")
                return True
            except Exception:
                time.sleep(5)
                if self.process.poll() is not None:
                    log.error(f"[SGLang] 服务器启动失败，退出码: {self.process.returncode}")
                    # 记录服务器日志最后内容
                    self._log_server_error()
                    return False

        log.error("[SGLang] 服务器启动超时")
        self._log_server_error()
        return False

    def _log_server_error(self):
        """记录服务器错误日志"""
        if self.server_log_file and self.server_log_file.exists():
            try:
                with open(self.server_log_file, "r") as f:
                    lines = f.readlines()
                    last_lines = lines[-50:] if len(lines) > 50 else lines
                    log.error("服务器日志 (最后50行):")
                    for line in last_lines:
                        log.error(f"  {line.rstrip()}")
            except Exception as e:
                log.error(f"读取服务器日志失败: {e}")

    def stop(self):
        """停止服务器"""
        if self.process:
            log.info(f"[SGLang] 停止服务器 (PID: {self.process.pid})")
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=10)
                log.debug("服务器已正常停止")
            except Exception as e:
                log.warning(f"正常停止失败，强制终止: {e}")
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except Exception:
                    pass
            self.process = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()


class BenchmarkRunner:
    """基准测试运行器"""

    def __init__(self, port: int, max_tokens: int = DEFAULT_MAX_TOKENS, thinking_mode: Optional[str] = None, temperature: float = 1.0):
        self.port = port
        self.max_tokens = max_tokens
        self.thinking_mode = thinking_mode
        self.temperature = temperature
        self.benchmark_log_dir = Path(DEFAULT_LOG_DIR) / "benchmarks"
        self.benchmark_log_dir.mkdir(parents=True, exist_ok=True)

    def run_gpqa(self, num_examples: int) -> Dict[str, Any]:
        """运行 GPQA 测试"""
        log.info(f"[GPQA] 运行测试 ({num_examples} samples, max_tokens={self.max_tokens})...")

        cmd = [
            "python", "-m", "sglang.test.run_eval",
            "--eval-name", "gpqa",
            "--port", str(self.port),
            "--num-examples", str(num_examples),
            "--max-tokens", str(self.max_tokens),
            "--repeat", "1",
            "--temperature", str(self.temperature),
        ]

        if self.thinking_mode:
            cmd.extend(["--thinking-mode", self.thinking_mode])

        result = self._run_command(cmd, "GPQA")
        accuracy = self._parse_accuracy(result)

        log.info(f"[GPQA] 完成 - 准确率: {accuracy:.2%}" if accuracy else "[GPQA] 完成 - 未能解析准确率")

        return {
            "accuracy": accuracy,
            "samples": num_examples,
            "max_tokens": self.max_tokens,
            "raw_output": result[-500:] if result else None,
        }

    def run_mmlu(self, num_examples: int) -> Dict[str, Any]:
        """运行 MMLU 测试"""
        log.info(f"[MMLU] 运行测试 ({num_examples} samples, max_tokens={self.max_tokens})...")

        cmd = [
            "python", "-m", "sglang.test.run_eval",
            "--eval-name", "mmlu",
            "--port", str(self.port),
            "--num-examples", str(num_examples),
            "--max-tokens", str(self.max_tokens),
            "--temperature", str(self.temperature),
        ]

        result = self._run_command(cmd, "MMLU")
        accuracy = self._parse_accuracy(result)

        log.info(f"[MMLU] 完成 - 准确率: {accuracy:.2%}" if accuracy else "[MMLU] 完成 - 未能解析准确率")

        return {
            "accuracy": accuracy,
            "samples": num_examples,
            "max_tokens": self.max_tokens,
            "raw_output": result[-500:] if result else None,
        }

    def run_gsm8k(self, num_questions: int, num_shots: int = 5) -> Dict[str, Any]:
        """运行 GSM8K 测试"""
        log.info(f"[GSM8K] 运行测试 ({num_questions} questions)...")

        cmd = [
            "python", "-m", "sglang.test.few_shot_gsm8k",
            "--host", "127.0.0.1",
            "--port", str(self.port),
            "--num-questions", str(num_questions),
            "--num-shots", str(num_shots),
        ]

        result = self._run_command(cmd, "GSM8K")
        accuracy = self._parse_accuracy(result)

        log.info(f"[GSM8K] 完成 - 准确率: {accuracy:.2%}" if accuracy else "[GSM8K] 完成 - 未能解析准确率")

        return {
            "accuracy": accuracy,
            "samples": num_questions,
            "raw_output": result[-500:] if result else None,
        }

    def run_humaneval(self, num_examples: int) -> Dict[str, Any]:
        """运行 HumanEval 测试"""
        log.info(f"[HumanEval] 运行测试 ({num_examples} samples)...")

        # 确保安装了 human_eval
        log.debug("检查 human_eval 包...")
        subprocess.run(["pip", "install", "human_eval", "-q"], capture_output=True)

        cmd = [
            "python", "-m", "sglang.test.run_eval",
            "--eval-name", "humaneval",
            "--port", str(self.port),
            "--num-examples", str(num_examples),
            "--temperature", str(self.temperature),
        ]

        result = self._run_command(cmd, "HumanEval")
        accuracy = self._parse_accuracy(result)

        log.info(f"[HumanEval] 完成 - 准确率: {accuracy:.2%}" if accuracy else "[HumanEval] 完成 - 未能解析准确率")

        return {
            "accuracy": accuracy,
            "samples": num_examples,
            "raw_output": result[-500:] if result else None,
        }

    def run_hellaswag(self, num_questions: int, num_shots: int = 20) -> Dict[str, Any]:
        """运行 HellaSwag 测试"""
        log.info(f"[HellaSwag] 运行测试 ({num_questions} questions)...")

        cmd = [
            "python", "benchmark/hellaswag/bench_sglang.py",
            "--host", "127.0.0.1",
            "--port", str(self.port),
            "--num-questions", str(num_questions),
            "--num-shots", str(num_shots),
        ]

        result = self._run_command(cmd, "HellaSwag")
        accuracy = self._parse_accuracy(result)

        log.info(f"[HellaSwag] 完成 - 准确率: {accuracy:.2%}" if accuracy else "[HellaSwag] 完成 - 未能解析准确率")

        return {
            "accuracy": accuracy,
            "samples": num_questions,
            "raw_output": result[-500:] if result else None,
        }

    def run_latency_test(self, num_prompts: int = 10) -> Dict[str, Any]:
        """运行延迟测试"""
        log.info(f"[性能] 延迟测试 ({num_prompts} prompts)...")

        cmd = [
            "python", "-m", "sglang.bench_serving",
            "--backend", "sglang",
            "--port", str(self.port),
            "--dataset-name", "random",
            "--num-prompts", str(num_prompts),
            "--max-concurrency", "1",
        ]

        result = self._run_command(cmd, "延迟测试")
        ttft = self._parse_ttft(result)

        log.info(f"[性能] TTFT: {ttft:.2f}ms" if ttft else "[性能] 未能解析 TTFT")

        return {
            "ttft_ms": ttft,
            "num_prompts": num_prompts,
            "raw_output": result[-500:] if result else None,
        }

    def run_throughput_test(self, num_prompts: int = 500, concurrency: int = 100) -> Dict[str, Any]:
        """运行吞吐量测试"""
        log.info(f"[性能] 吞吐量测试 ({num_prompts} prompts, concurrency={concurrency})...")

        cmd = [
            "python", "-m", "sglang.bench_serving",
            "--backend", "sglang",
            "--port", str(self.port),
            "--dataset-name", "random",
            "--num-prompts", str(num_prompts),
            "--max-concurrency", str(concurrency),
        ]

        result = self._run_command(cmd, "吞吐量测试")
        throughput = self._parse_throughput(result)

        log.info(f"[性能] 吞吐量: {throughput:.2f} tok/s" if throughput else "[性能] 未能解析吞吐量")

        return {
            "throughput_tokens_per_sec": throughput,
            "num_prompts": num_prompts,
            "concurrency": concurrency,
            "raw_output": result[-500:] if result else None,
        }

    def _run_command(self, cmd: List[str], name: str, timeout: int = 3600) -> str:
        """运行命令并返回输出（后台执行，完整日志记录，错误立即上报）"""
        log.log_command(cmd)
        cmd = list(map(str, cmd))

        # 创建日志文件路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = name.replace(" ", "_").lower()
        log_file = self.benchmark_log_dir / f"{safe_name}_{timestamp}.log"

        log.debug(f"基准测试日志文件: {log_file}")

        try:
            # 后台执行命令，输出写入日志文件
            with open(log_file, "w") as f:
                f.write(f"基准测试: {name}\n")
                f.write(f"时间: {datetime.now().isoformat()}\n")
                f.write(f"命令: {' '.join(cmd)}\n")
                f.write("=" * 60 + "\n\n")
                f.flush()

                process = subprocess.Popen(
                    cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )

                # 等待进程完成
                process.wait(timeout=timeout)

            # 读取完整日志输出
            with open(log_file, "r") as f:
                output = f.read()

            # 记录到主日志（截断）
            log.log_output(output)

            # 错误立即上报
            if process.returncode != 0:
                error_msg = f"[错误] {name} 返回非零退出码: {process.returncode}"
                log.error(error_msg)
                # 立即上报错误到结果
                raise RuntimeError(error_msg)

            return output

        except subprocess.TimeoutExpired:
            error_msg = f"[错误] {name} 命令超时 ({timeout}s)"
            log.error(error_msg)
            # 记录超时到日志文件
            with open(log_file, "a") as f:
                f.write(f"\n{error_msg}\n")
            raise RuntimeError(error_msg)
        except RuntimeError:
            # 已经是错误消息，直接向上传递
            raise
        except Exception as e:
            error_msg = f"[错误] {name} 执行失败 - {str(e)}"
            log.error(error_msg)
            raise RuntimeError(error_msg)

    def _parse_accuracy(self, output: str) -> Optional[float]:
        """从输出中解析准确率"""
        if not output:
            return None

        patterns = [
            r"score[:\s=]+([0-9.]+)",  # SGLang 输出格式: score=0.1616
            r"accuracy[:\s=]+([0-9.]+)",
            r"Accuracy[:\s=]+([0-9.]+)",
            r"([\d.]+)%\s*(?:accuracy|correct)",
            r"pass@1[:\s=]+([0-9.]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if value > 1:
                    value = value / 100
                return value

        return None

    def _parse_ttft(self, output: str) -> Optional[float]:
        """解析 TTFT"""
        if not output:
            return None

        patterns = [
            r"TTFT[:\s]+([0-9.]+)\s*ms",
            r"time to first token[:\s]+([0-9.]+)\s*ms",
            r"mean_ttft_ms[:\s]+([0-9.]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return float(match.group(1))

        return None

    def _parse_throughput(self, output: str) -> Optional[float]:
        """解析吞吐量"""
        if not output:
            return None

        patterns = [
            r"throughput[:\s]+([0-9.]+)\s*tokens?/s",
            r"output token throughput[:\s]+([0-9.]+)",
            r"total tokens?/s[:\s]+([0-9.]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return float(match.group(1))

        return None


class ModelEvaluator:
    """模型评估器"""

    def __init__(self, args):
        self.args = args
        self.model_path = args.model_path
        self.model_name = self._extract_model_name(args.model_path)
        self.start_time = datetime.now()
        self.results = {
            "status": "pending",
            "model_id": self.model_path,
            "model_name": self.model_name,
            "evaluation_time": self.start_time.isoformat(),
            "environment": self._get_environment(),
            "benchmarks": {},
            "performance": {},
            "errors": [],
            "log_file": log.get_log_path(),
            "benchmark_log_dir": str(Path(DEFAULT_LOG_DIR) / "benchmarks"),
        }

    def _extract_model_name(self, model_path: str) -> str:
        """提取模型名称"""
        return model_path.split("/")[-1] if "/" in model_path else model_path

    def _get_environment(self) -> Dict[str, Any]:
        """获取环境信息"""
        env = {
            "tp_size": self.args.tp,
            "port": self.args.port,
        }

        # 尝试获取 GPU 信息
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                env["gpu"] = result.stdout.strip().split("\n")[0]
                log.debug(f"GPU: {env['gpu']}")
        except Exception:
            log.debug("无法获取 GPU 信息")

        # 尝试获取 SGLang 版本
        try:
            result = subprocess.run(
                ["python", "-c", "import sglang; print(sglang.__version__)"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                env["sglang_version"] = result.stdout.strip()
                log.debug(f"SGLang 版本: {env['sglang_version']}")
        except Exception:
            log.debug("无法获取 SGLang 版本")

        return env

    def _parse_num_examples(self, arg: str) -> Dict[str, int]:
        """解析样本数参数"""
        result = {}
        if not arg:
            return DEFAULT_NUM_EXAMPLES

        for item in arg.split(","):
            if ":" in item:
                name, num = item.split(":")
                result[name.strip()] = int(num.strip())
            else:
                name = item.strip()
                result[name] = DEFAULT_NUM_EXAMPLES.get(name, 100)

        return result

    def run(self) -> Dict[str, Any]:
        """运行完整评估"""
        server = None
        try:
            # 启动服务器
            server = SGLangServer(
                self.model_path,
                self.args.port,
                self.args.tp,
                self.args.mem_fraction
            )

            if not server.start(timeout=self.args.server_timeout):
                self.results["status"] = "error"
                self.results["errors"].append("服务器启动失败")
                return self.results

            # 创建测试运行器
            runner = BenchmarkRunner(
                self.args.port,
                max_tokens=self.args.max_tokens,
                thinking_mode=self.args.thinking_mode,
                temperature=self.args.temperature
            )

            # 解析样本数配置
            num_examples = self._parse_num_examples(self.args.num_examples)

            # 运行基准测试
            benchmarks = [b.strip() for b in self.args.benchmarks.split(",")]

            for benchmark in benchmarks:
                start_time = time.time()

                try:
                    if benchmark == "gpqa":
                        result = runner.run_gpqa(num_examples.get("gpqa", 198))
                    elif benchmark == "mmlu":
                        result = runner.run_mmlu(num_examples.get("mmlu", 1000))
                    elif benchmark == "gsm8k":
                        result = runner.run_gsm8k(num_examples.get("gsm8k", 200))
                    elif benchmark == "humaneval":
                        result = runner.run_humaneval(num_examples.get("humaneval", 164))
                    elif benchmark == "hellaswag":
                        result = runner.run_hellaswag(num_examples.get("hellaswag", 200))
                    else:
                        log.warning(f"未知的基准测试: {benchmark}")
                        continue

                    result["duration_seconds"] = round(time.time() - start_time, 2)
                    self.results["benchmarks"][benchmark] = result

                except Exception as e:
                    self.results["errors"].append(f"{benchmark}: {str(e)}")
                    log.error(f"{benchmark} 测试失败: {e}")

            # 运行性能测试
            if self.args.performance:
                try:
                    latency_result = runner.run_latency_test()
                    self.results["performance"]["latency"] = latency_result
                except Exception as e:
                    self.results["errors"].append(f"延迟测试: {str(e)}")
                    log.error(f"延迟测试失败: {e}")

                try:
                    throughput_result = runner.run_throughput_test()
                    self.results["performance"]["throughput"] = throughput_result
                except Exception as e:
                    self.results["errors"].append(f"吞吐量测试: {str(e)}")
                    log.error(f"吞吐量测试失败: {e}")

            self.results["status"] = "success" if not self.results["errors"] else "partial"

        except Exception as e:
            self.results["status"] = "error"
            self.results["errors"].append(str(e))
            log.error(f"评估过程异常: {e}")

        finally:
            if server:
                server.stop()

        # 计算总耗时
        total_duration = (datetime.now() - self.start_time).total_seconds()
        self.results["total_duration_seconds"] = round(total_duration, 2)
        log.info(f"总耗时: {total_duration:.2f}s")

        # 生成报告
        self._generate_report()

        return self.results

    def _generate_report(self) -> str:
        """生成报告文件"""
        report_dir = Path(self.args.report_path or DEFAULT_REPORT_DIR)
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"{self.model_name}_{timestamp}"

        # 根据输出格式生成报告
        if self.args.output == "json":
            report_file = report_file.with_suffix(".json")
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
        else:
            report_file = report_file.with_suffix(".md")
            self._write_markdown_report(report_file)

        self.results["report_path"] = str(report_file)
        log.info(f"报告已保存: {report_file}")

        return str(report_file)

    def _write_markdown_report(self, report_file: Path):
        """写入 Markdown 报告"""
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"# 模型评估报告: {self.model_name}\n\n")
            f.write(f"- **模型路径**: {self.model_path}\n")
            f.write(f"- **评估时间**: {self.results['evaluation_time']}\n")
            f.write(f"- **状态**: {self.results['status']}\n")
            f.write(f"- **日志文件**: {self.results.get('log_file', 'N/A')}\n\n")

            # 环境信息
            env = self.results.get("environment", {})
            f.write("## 环境信息\n\n")
            for key, value in env.items():
                f.write(f"- {key}: {value}\n")
            f.write("\n")

            # 基准测试结果
            if self.results.get("benchmarks"):
                f.write("## 基准测试结果\n\n")
                f.write("| Benchmark | Accuracy | Samples | Duration |\n")
                f.write("|-----------|----------|---------|----------|\n")

                for name, result in self.results["benchmarks"].items():
                    acc = result.get("accuracy")
                    acc_str = f"{acc:.2%}" if acc is not None else "N/A"
                    samples = result.get("samples", "N/A")
                    duration = result.get("duration_seconds", "N/A")
                    f.write(f"| {name} | {acc_str} | {samples} | {duration}s |\n")
                f.write("\n")

            # 性能测试结果
            if self.results.get("performance"):
                f.write("## 性能测试结果\n\n")
                perf = self.results["performance"]

                if "latency" in perf:
                    lat = perf["latency"]
                    ttft = lat.get("ttft_ms")
                    ttft_str = f"{ttft:.2f}ms" if ttft is not None else "N/A"
                    f.write(f"- **TTFT (首Token延迟)**: {ttft_str}\n")

                if "throughput" in perf:
                    thr = perf["throughput"]
                    tps = thr.get("throughput_tokens_per_sec")
                    tps_str = f"{tps:.2f} tok/s" if tps is not None else "N/A"
                    f.write(f"- **吞吐量**: {tps_str}\n")

                f.write("\n")

            # 错误信息
            if self.results.get("errors"):
                f.write("## 错误信息\n\n")
                for error in self.results["errors"]:
                    f.write(f"- {error}\n")


def _run_as_daemon(args):
    """以后台守护进程模式运行评估"""
    # 创建必要的目录
    daemon_log_dir = Path(DEFAULT_LOG_DIR)
    daemon_log_dir.mkdir(parents=True, exist_ok=True)

    # PID 文件路径
    pid_file = daemon_log_dir / "eval_model.pid"

    # 检查是否已有进程在运行
    if pid_file.exists():
        try:
            with open(pid_file, "r") as f:
                old_pid = int(f.read().strip())
            # 检查进程是否存在
            os.kill(old_pid, 0)
            print(f"评估任务已在运行中 (PID: {old_pid})")
            log_file_pattern = daemon_log_dir / f"model_eval_{datetime.now().strftime('%Y%m%d')}.log"
            print(f"日志文件: {log_file_pattern}")
            sys.exit(1)
        except (ProcessLookupError, ValueError):
            # 进程不存在，删除旧的 PID 文件
            pid_file.unlink()

    # 构建不带 --daemon 的命令
    cmd = [sys.executable, __file__]
    for key, value in vars(args).items():
        if key == "daemon" or value is None or value is False:
            continue
        key = key.replace("_", "-")
        if isinstance(value, bool) and value:
            cmd.append(f"--{key}")
        else:
            cmd.extend([f"--{key}", str(value)])

    # 日志文件
    log_file = daemon_log_dir / f"model_eval_{datetime.now().strftime('%Y%m%d')}.log"

    print("=" * 60)
    print("启动后台评估任务")
    print("=" * 60)
    print(f"模型: {args.model_path}")
    print(f"基准测试: {args.benchmarks}")
    print(f"日志文件: {log_file}")
    print(f"PID 文件: {pid_file}")
    print("=" * 60)

    # 启动后台进程
    with open(log_file, "a") as f:
        f.write(f"\n{'=' * 60}\n")
        f.write(f"后台任务启动: {datetime.now().isoformat()}\n")
        f.write(f"命令: {' '.join(cmd)}\n")
        f.write(f"{'=' * 60}\n\n")
        f.flush()

        process = subprocess.Popen(
            cmd,
            stdout=f,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )

        # 保存 PID
        with open(pid_file, "w") as pf:
            pf.write(str(process.pid))

    print(f"\n✓ 任务已启动 (PID: {process.pid})")
    print(f"\n查看进度:")
    print(f"  tail -f {log_file}")
    print(f"\n检查任务状态:")
    print(f"  ps -p {process.pid}")
    print(f"\n停止任务:")
    print(f"  kill {process.pid}")

    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="SGLang 模型评估脚本 - 自动化运行基准测试和性能测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--model_path",
        help="模型路径、ID 或名称。支持: 1) 本地绝对路径 2) HuggingFace/ModelScope ID (如 Qwen/Qwen2.5-7B) 3) 模型名称 (如 Qwen3.5-0.8B，自动从 ModelScope 下载到 /workspace/models)"
    )

    parser.add_argument(
        "--model_dir",
        default=DEFAULT_MODEL_DIR,
        help=f"模型下载目录 (默认: {DEFAULT_MODEL_DIR})"
    )

    parser.add_argument(
        "--benchmarks",
        default="gpqa",
        help="要运行的基准测试，逗号分隔 (默认: gpqa)。使用 'all' 运行全部基准测试"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="运行全部基准测试 (gpqa,mmlu,gsm8k,humaneval,hellaswag)"
    )

    parser.add_argument(
        "--performance",
        action="store_true",
        default=False,
        help="运行性能测试 (延迟、吞吐量)"
    )

    parser.add_argument(
        "--no-performance",
        action="store_true",
        help="跳过性能测试（已默认跳过，此参数保留兼容）"
    )

    parser.add_argument(
        "--foreground",
        action="store_true",
        help="前台运行模式（默认后台运行）"
    )

    parser.add_argument(
        "--output",
        choices=["json", "markdown"],
        default="json",
        help="输出格式 (默认: json)"
    )

    parser.add_argument(
        "--report_path",
        help="报告保存目录 (默认: /workspace/eval_reports)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"SGLang 服务端口 (默认: {DEFAULT_PORT})"
    )

    parser.add_argument(
        "--tp",
        type=int,
        default=DEFAULT_TP,
        help=f"Tensor 并行数 (默认: {DEFAULT_TP})"
    )

    parser.add_argument(
        "--mem_fraction",
        type=float,
        default=DEFAULT_MEM_FRACTION,
        help=f"GPU 内存占用比例 (默认: {DEFAULT_MEM_FRACTION})"
    )

    parser.add_argument(
        "--num_examples",
        help="各基准测试样本数，格式: gpqa:100,mmlu:500"
    )

    parser.add_argument(
        "--thinking_mode",
        choices=["qwen3", "deepseek-v3"],
        help="推理模式，用于支持 thinking 的模型"
    )

    parser.add_argument(
        "--server_timeout",
        type=int,
        default=300,
        help="服务器启动超时时间 (默认: 300s)"
    )

    parser.add_argument(
        "--max_tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"评估时最大 token 数 (默认: {DEFAULT_MAX_TOKENS})"
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=1.0,
        help="生成温度参数 (默认: 1.0)"
    )

    args = parser.parse_args()

    # 处理性能测试标志
    if args.no_performance:
        args.performance = False

    # 处理 --all 参数
    if args.all:
        args.benchmarks = "gpqa,mmlu,gsm8k,humaneval,hellaswag"

    # 处理 benchmarks 参数中的 "all"
    if args.benchmarks.lower() == "all":
        args.benchmarks = "gpqa,mmlu,gsm8k,humaneval,hellaswag"

    # 默认后台运行，除非指定 --foreground
    if not args.foreground:
        _run_as_daemon(args)
        return

    # 解析模型路径
    downloader = ModelDownloader(args.model_dir)
    try:
        resolved_model_path = downloader.resolve_model_path(args.model_path) if args.model_path else None

        if not resolved_model_path:
            log.error("未指定模型路径，请使用 --model_path 参数")
            sys.exit(1)

        args.model_path = resolved_model_path
    except Exception as e:
        log.error(f"模型路径解析失败: {e}")
        sys.exit(1)

    # 记录评估开始
    log.log_section("SGLang 模型评估")
    log.info(f"模型输入: {args.model_path if hasattr(args, '_raw_model_path') else args.model_path}")
    log.info(f"模型路径: {args.model_path}")
    log.info(f"基准测试: {args.benchmarks}")
    log.info(f"性能测试: {'是' if args.performance else '否'}")
    log.info(f"输出格式: {args.output}")
    log.info(f"日志文件: {log.get_log_path()}")

    evaluator = ModelEvaluator(args)
    results = evaluator.run()

    # 输出结果摘要
    log.log_section("评估结果摘要")
    log.info(f"状态: {results['status'].upper()}")
    log.info(f"总耗时: {results.get('total_duration_seconds', 'N/A')}s")

    if results.get("benchmarks"):
        log.info("")
        log.info("基准测试结果:")
        for name, result in results["benchmarks"].items():
            acc = result.get("accuracy")
            acc_str = f"{acc:.2%}" if acc is not None else "N/A"
            duration = result.get("duration_seconds", "N/A")
            log.info(f"  - {name}: {acc_str} ({duration}s)")

    if results.get("performance"):
        log.info("")
        log.info("性能指标:")
        if "latency" in results["performance"]:
            ttft = results["performance"]["latency"].get("ttft_ms")
            if ttft:
                log.info(f"  - TTFT: {ttft:.2f}ms")
        if "throughput" in results["performance"]:
            tps = results["performance"]["throughput"].get("throughput_tokens_per_sec")
            if tps:
                log.info(f"  - 吞吐量: {tps:.2f} tok/s")

    if results.get("errors"):
        log.warning(f"\n错误: {len(results['errors'])} 个")
        for err in results["errors"]:
            log.warning(f"  - {err}")

    if results.get("report_path"):
        log.info(f"\n报告路径: {results['report_path']}")

    log.info(f"\n日志文件: {results.get('log_file')}")

    # 返回退出码
    sys.exit(0 if results["status"] == "success" else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv


# 加载 project-root/ 根目录下的 .env（用户指定路径）
REPO_ROOT = Path(__file__).parent.parent.resolve()
print(f"REPO_ROOT={REPO_ROOT}")
load_dotenv(dotenv_path=REPO_ROOT / ".env")

sys.path.insert(0, str(REPO_ROOT))

from harness.budget import BudgetGuard 
from harness.config import HarnessConfig 
from harness.core import run_agent  
from harness.hooks import HookManager 
from harness.permission import PermissionGate 
from harness.planner import reset_todos, todo_tool 
from harness.tool_file_ops import read_file, write_file, edit_file 
from harness.progress import ProgressTracker 
from harness.console import ConsolePrinter 
from harness.verifier import SYSTEM_PROMPT_WITH_VERIFICATION 


# ---- 配置 ----
# 默认走 DeepSeek 直连（对当前网络更稳、成本更低）
MODEL_NAME = os.getenv("DEMO_MODEL", "deepseek-chat")
API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

import sys

OUTPUT_DIR = REPO_ROOT / "demo_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ====================================================================
# Demo 2: Full Harness Agent（10 机制全开）
# ====================================================================
def run_full_harness(user_goal: str) -> dict:
    print("\n" + "=" * 60)
    print("[Full Harness] 开始运行")
    print("=" * 60)

    reset_todos()

    # 1) Hooks 事件总线
    hooks = HookManager()

    # 2) Progress Tracker（写 progress.md）
    progress_path = OUTPUT_DIR / "progress.md"
    # 每次 demo 重置 progress.md，避免历史累积
    progress_path.unlink(missing_ok=True)
    tracker = ProgressTracker(str(progress_path))
    tracker.register_to(hooks)

    # 3) Permission Gate（挂 pre_tool_use）
    gate = PermissionGate()
    gate.register_to(hooks)

    # 4) Token Budget（10 轮任务上限 $0.50）
    # 默认按 claude-sonnet-4.6 档次定价；DeepSeek 更便宜，此处留大额缓冲
    budget = BudgetGuard(
        max_usd=0.50,
        price_per_1k_input=0.003,
        price_per_1k_output=0.015,
    )
    budget.register_to(hooks)

    printer = ConsolePrinter()
    printer.register_to(hooks)

    tools = {
        "read_file": read_file,
        "write_file": write_file,
        "edit_file": edit_file,
    }

    config = HarnessConfig(
        api_key=API_KEY,
        base_url=BASE_URL,
        model_name=MODEL_NAME,
        max_steps=10,
    )

    # 增强 prompt：让 agent 规划 → 分析 → 收束
    enhanced_goal = f"""
你是一个文档编辑工作者，负责根据用户需求编辑文档。
用户需求：{user_goal}

文档输出要求：
- 文件保存路径：{OUTPUT_DIR}
- 文件名称：根据用户需求生成
```
"""

    t0 = time.time()
    result = run_agent(
        user_goal=enhanced_goal,
        tools=tools,
        config=config,
        system_prompt=SYSTEM_PROMPT_WITH_VERIFICATION,
        hooks=hooks,
        budget=budget,
    )
    elapsed = time.time() - t0

    result["elapsed_seconds"] = round(elapsed, 2)
    result["tokens_total"] = result.get("tokens", 0)

    print(
        f"  steps={result['steps']}  elapsed={result['elapsed_seconds']}s  "
        f"tokens={result['tokens_total']}  blocked={result['blocked_tools']}  "
        f"errors={len(result['errors'])}"
    )
    
    print(f"  progress.md 写入：{progress_path}")

    return result

def _retry(fn, attempts: int = 5, delay: float = 5.0, label: str = "call"):
    """对 fn 做简单重试，应对偶发 TLS / 网络错误。"""
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last = e
            print(f"  ⚠️ {label} attempt {i+1}/{attempts} failed: {type(e).__name__}: {e}")
            if i < attempts - 1:
                time.sleep(delay)
    raise last


def main():
    if not API_KEY:
        print("❌ 缺少 API_KEY，请检查 project-root/.env")
        sys.exit(1)

    print("=" * 60)
    print(f"模型：{MODEL_NAME}")
    print("=" * 60)

    user_goal = "根据李白的《春夜》写一篇关于春夜的诗"

    _retry(lambda: run_full_harness(user_goal), label="harness")
    

    print("\n" + "=" * 60)
    print("✅ E2E Demo 完成")
    print("=" * 60)


if __name__ == "__main__":
    main()

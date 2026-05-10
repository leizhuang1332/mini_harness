"""
控制台打印
"""

import json
import datetime
from typing import Any, Dict


class ConsolePrinter:
    """
    Console Printer 实现，通过 hook 机制与 core.run_agent 解耦。

    使用方式：
        printer = ConsolePrinter()
        hooks = HookManager()
        printer.register_to(hooks)
        run_agent(goal, tools, config, hooks=hooks)
    """

    def __init__(self, max_content_len: int = 200):
        """
        Args:
            max_content_len: 每条日志最多保留多少字符（避免 tool result 撑爆文件）
        """
        self.max_content_len = max_content_len
        self.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self._entry_count = 0

    def register_to(self, hooks) -> None:
        """挂载到 HookManager 的三个事件。"""
        hooks.register("session_start", self.on_session_start)
        hooks.register("post_tool_use", self.on_post_tool_use)
        hooks.register("post_llm", self.on_post_llm)
        hooks.register("session_stop", self.on_session_stop)

    def on_session_start(self, user_goal: str = "") -> None:
        """session 开始时写入分隔线和目标。"""
        ts = self._timestamp()
        content = (
            f"\n{'-' * 60}\n"
            f"{ts} · User@{self.session_id} : \n"
            f"\n"
            f"{user_goal}\n"
        )
        self._print(content)

    def on_post_tool_use(
        self,
        tool_name: str = "",
        tool_args: Dict[str, Any] = None,
        result: Any = "",
    ) -> None:
        """每次 tool call 后打印。"""
        self._entry_count += 1
        ts = self._timestamp()
        args_str = self._safe_json(tool_args or {})
        content = (
            f"\n{'-' * 60}\n"
            f"\n{ts} · Tool@{tool_name} · args: {args_str}\n"
            f"\n"
            f"{json.loads(result)}\n"
        )
        self._print(content)

    def on_session_stop(
        self,
        answer: Any = "",
        metrics: Dict[str, Any] = None,
    ) -> None:
        ts = self._timestamp()
        metrics = metrics or {}
        content = (
            f"\n{'-' * 60}\n"
            f"\nCompleted {self.session_id} ended at {ts}\n"
            f"\n{ts} · Completed · final answer: \n"
            f"\n"
            f"{answer}\n"
        )
        self._print(content)

    def on_post_llm(self, steps: int, response: Any) -> None:
        """每次LLM调用后的事件处理"""
        ts = self._timestamp()
        content = (
            f"\n{'-' * 60}\n"
            f"\n{ts} · LLM@{steps} · response: \n"
            f"\n"
            f"{response.choices[0].message.content}\n"
        )
        self._print(content)

    def _print(self, text: str) -> None:
        print(text)

    def _timestamp(self) -> str:
        return datetime.datetime.now().isoformat(timespec="seconds")

    def _safe_json(self, obj) -> str:
        try:
            return json.dumps(obj, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(obj)

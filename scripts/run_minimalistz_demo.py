from dotenv import load_dotenv
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
print(f"REPO_ROOT={REPO_ROOT}")
load_dotenv(dotenv_path=REPO_ROOT / ".env")

sys.path.insert(0, str(REPO_ROOT))

# 读取 API Key（DeepSeek 直连或 OpenRouter）
api_key = os.getenv("DEEPSEEK_API_KEY")
base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
model = os.getenv("DEMO_MODEL")

import json
from openai import OpenAI

client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)

# 第一部分：定义工具函数
def add(a: int, b: int) -> int:
    """将两个整数相加"""
    return a + b

def get_weather(city: str) -> str:
    """查询城市天气（Mock 数据）"""
    return f"{city}：晴天，25°C"

# 工具注册表
TOOLS = {
    "add": add,
    "get_weather": get_weather,
}

# 第二部分：手写 tool schema（让学员感受这个痛点）
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "将两个整数相加",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "第一个数"},
                    "b": {"type": "integer", "description": "第二个数"},
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询城市天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名"},
                },
                "required": ["city"],
            },
        },
    },
]

# 第三部分：Agent 循环核心
def run_agent(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]

    round_num = 0
    while True:
        round_num += 1
        print(f"\n===== 第 {round_num} 轮 LLM 调用 =====")

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
        )
        msg = response.choices[0].message
        messages.append(msg)

        # 没有工具调用 → 任务完成
        if not msg.tool_calls:
            print(f"最终回答：{msg.content}")
            return msg.content

        # 执行所有工具调用
        for call in msg.tool_calls:
            name   = call.function.name
            args   = json.loads(call.function.arguments)
            result = TOOLS[name](**args)
            print(f"  调用工具: {name}({args}) => {result}")

            messages.append({
                "role":         "tool",
                "tool_call_id": call.id,
                "content":      str(result),
            })

def main():
    run_agent("北京今天天气怎么样？另外 88 加 99 等于多少？")

if __name__ == "__main__":
    main()

# ===== 第 1 轮 LLM 调用 =====
#   调用工具: get_weather({'city': '北京'}) => 北京：晴天，25°C
#   调用工具: add({'a': 88, 'b': 99}) => 187

# ===== 第 2 轮 LLM 调用 =====
# 最终回答：来为您解答：

# ### 🌤️ 北京今天天气
# **晴天**，气温 **25°C**，天气不错哦！

# ### ➕ 数学计算
# **88 + 99 = 187**

# 还有其他问题吗？😊
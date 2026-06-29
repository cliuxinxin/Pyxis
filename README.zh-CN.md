# Pyxis

一个极简、以人为中心、可控的 Python Agent Harness。

Pyxis 这个名字来自古代航海罗盘座。它强调的不是让 Agent 盲目自动化，而是帮助人和
Agent 一起判断方向、推进任务、保持控制。

## 核心理念

Pyxis 的核心不是 `Agent.run()`，而是 `Session.navigate()`。

对话不是附属输入框，而是控制 Agent 的界面。Pyxis 会通过 `Compass` 判断下一步应该：

- 追问
- 提出计划
- 执行
- 请求确认
- 停止

## 核心抽象

- `Session`：人与 Agent 的共同工作上下文
- `Dialogue`：语义化对话状态
- `Compass`：导航和决策层
- `Checkpoint`：人类确认点
- `ControlPolicy`：控制策略
- `Agent`：执行体
- `Tool`：工具
- `Workflow`：可观察、可中断的任务流基础
- `Provider`：模型供应商接口

## 快速开始

```python
from pyxis import Agent, MockProvider, Pyxis

agent = Agent(
    name="navigator",
    instructions="Help the user move through work calmly and clearly.",
    provider=MockProvider(output="这是一个简洁计划。"),
)

session = Pyxis(agent=agent).session()
result = session.navigate("帮我规划一个竞品研究流程")

print(result.output)
```

## OpenAI-Compatible Provider

Pyxis 可以连接兼容 OpenAI Chat Completions 协议的接口，不强制依赖某个 SDK。

推荐通过环境变量配置：

```bash
export OPENAI_BASE_URL="https://ark.cn-beijing.volces.com/api/coding/v3"
export OPENAI_API_KEY="..."
export OPENAI_MODEL="your-model"
```

然后这样使用：

```python
import os

from pyxis import Agent, OpenAICompatibleProvider, Pyxis

provider = OpenAICompatibleProvider(
    model=os.environ["OPENAI_MODEL"],
)

agent = Agent(
    name="navigator",
    instructions="Help the user move through work calmly and clearly.",
    provider=provider,
)

result = Pyxis(agent=agent).navigate("帮我规划一个竞品研究流程")
print(result.output)
```

真实 key 不要提交到仓库。仓库里只保留 `.env.example` 作为配置示例。

### Live Smoke Test

先复制一份本地环境变量文件：

```bash
cp .env.example .env.local
```

然后在 `.env.local` 里填入 `OPENAI_API_KEY` 和 `OPENAI_MODEL`。这个文件已经被
git 忽略，不会被提交。

运行示例：

```bash
PYTHONPATH=src python3 examples/basic_openai_compatible.py
```

示例会读取 `.env.local`，调用配置好的 OpenAI-compatible provider，并打印 Agent
返回结果。

如果想测试真实模型是否会遵循 Pyxis tool-call JSON 协议，可以运行：

```bash
PYTHONPATH=src python3 examples/agent_tool_call.py
```

这个示例暴露一个低风险工具和一个高风险工具。低风险工具应该直接执行；高风险工具应该暂停并生成 checkpoint。

## 可控工具调用

通过 `Session` 调用工具时，Pyxis 会根据 `ControlPolicy` 判断是否需要 checkpoint。

```python
from pyxis import Agent, Pyxis, tool

@tool(risk="high", action="file_write")
def write_file(path: str, content: str) -> str:
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)
    return path

session = Pyxis(
    agent=Agent(
        name="navigator",
        tools=[write_file],
    )
).session()

result = session.call_tool("write_file", "notes.txt", content="hello")

if result.requires_confirmation:
    checkpoint = result.checkpoint
    session.approve_checkpoint(checkpoint.id)
    result = session.resume_checkpoint(checkpoint.id)

print(result.output)
```

高风险工具不会立刻执行，而是先暂停并生成 checkpoint。只有确认后，Pyxis 才会恢复执行。

## Agent 工具调用协议

Agent 可以通过一个轻量 JSON action 请求工具调用：

```json
{
  "type": "tool_call",
  "tool": "summarize",
  "args": {
    "text": "Pyxis helps agents move through work with control."
  }
}
```

`Session.navigate()` 会在 Agent 返回后解析这个协议。低风险工具会直接执行；高风险工具会复用
`session.call_tool()` 的 checkpoint 流程。

```python
from pyxis import Agent, MockProvider, Pyxis, tool

@tool(risk="low", action="summarize")
def summarize(text: str) -> str:
    return text[:32]

agent = Agent(
    name="navigator",
    provider=MockProvider(
        output='{"type":"tool_call","tool":"summarize","args":{"text":"Pyxis keeps humans in control."}}'
    ),
    tools=[summarize],
)

result = Pyxis(agent=agent).navigate("Summarize this")
print(result.output)
```

如果 Agent 返回的不是合法 action JSON，Pyxis 会把它当作普通文本消息处理。

当 Agent 挂载了工具时，Pyxis 会自动把工具清单和 action 协议注入到 provider
instructions 里。开发者只需要定义一次工具，Agent 会收到工具的 name、description、
risk 和 action 元信息。

## 当前状态

这是 Pyxis 的早期 MVP。第一版先建立清楚的骨架：

- `Session`
- `Compass`
- `Checkpoint`
- `Agent`
- `Tool`
- `Workflow`
- `MockProvider`

真实模型 provider、长期 memory、多 Agent 协作和更复杂 workflow 会在后续加入。

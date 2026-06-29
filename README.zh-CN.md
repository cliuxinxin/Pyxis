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

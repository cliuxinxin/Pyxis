# Memory

Pyxis has two memory layers:

- `SessionMemory` is bounded, in-process memory attached to an agent session.
- `MemoryStore` is a protocol for long-term, namespaced memory adapters.

Core Pyxis does not require a database, vector store, or web framework.
Applications can implement persistent adapters for SQLite, Postgres, or another
storage layer.

## Session Memory

Use `SessionMemory` for explicit preferences, project context, and scratchpad
state that should be visible in snapshots:

```python
from pyxis import Agent, Pyxis, SessionMemory

memory = SessionMemory()
memory.set_preference("tone", "concise")
memory.set_project_context(name="Astra")

session = Pyxis(agent=Agent(name="navigator", memory=memory)).session()
```

When a host application wants long-term memory to appear in session snapshots,
attach a store explicitly:

```python
from pyxis import InMemoryStore, SessionMemory

store = InMemoryStore()
store.set("user", "watchlist", ["agent frameworks"])

memory = SessionMemory(store=store)
```

## Long-Term Store Protocol

Use `MemoryStore` when an application needs durable, cross-session memory:

```python
from pyxis import InMemoryStore

store = InMemoryStore()
store.set(
    "user",
    "watchlist",
    ["agent frameworks", "model routing"],
    metadata={"source": "feedback"},
)

print(store.get("user", "watchlist"))
```

The protocol is intentionally small:

```python
class MemoryStore:
    def get(self, namespace, key, default=None): ...
    def set(self, namespace, key, value, *, metadata=None): ...
    def delete(self, namespace, key): ...
    def list(self, namespace): ...
```

Namespaces keep product concerns separate. For example, an application might use
`user`, `project`, `feedback`, and `briefing` namespaces.

## Persistent Adapters

Pyxis core provides `NoMemoryStore` and `InMemoryStore`. A product such as Astra
can implement:

- `SQLiteMemoryStore`
- `PostgresMemoryStore`
- a vector-backed store layered behind the same protocol

The adapter owns durability, migrations, indexes, and application-specific
query behavior. Pyxis owns the shape of the contract.

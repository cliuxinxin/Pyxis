"""Conversation state for a Pyxis session."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Role = Literal["user", "agent", "system"]


@dataclass(frozen=True)
class Message:
    """A single dialogue message."""

    role: Role
    content: str

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "content": self.content,
        }


@dataclass
class Dialogue:
    """Semantic conversation state, not just raw model messages."""

    messages: list[Message] = field(default_factory=list)
    user_goal: str | None = None
    open_questions: list[str] = field(default_factory=list)
    confirmations: list[str] = field(default_factory=list)

    def add(self, role: Role, content: str) -> Message:
        message = Message(role=role, content=content)
        self.messages.append(message)
        if role == "user" and self.user_goal is None:
            self.user_goal = content
        return message

    def latest_user_message(self) -> str | None:
        for message in reversed(self.messages):
            if message.role == "user":
                return message.content
        return None

    def to_dict(self) -> dict:
        return {
            "messages": [message.to_dict() for message in self.messages],
            "user_goal": self.user_goal,
            "open_questions": list(self.open_questions),
            "confirmations": list(self.confirmations),
        }

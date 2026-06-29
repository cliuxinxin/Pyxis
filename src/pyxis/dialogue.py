"""Conversation state for a Pyxis session."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

Role = Literal["user", "agent", "system"]


class IntentType(str, Enum):
    """Common intent categories for a human turn."""

    UNKNOWN = "unknown"
    CLARIFY = "clarify"
    PLAN = "plan"
    ACT = "act"
    CONFIRM = "confirm"
    STOP = "stop"


@dataclass(frozen=True)
class Intent:
    """A structured reading of what the user appears to want."""

    type: IntentType
    summary: str
    confidence: float = 1.0
    needs_clarification: bool = False

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "summary": self.summary,
            "confidence": self.confidence,
            "needs_clarification": self.needs_clarification,
        }


@dataclass(frozen=True)
class UserGoal:
    """The working goal Pyxis is helping the user clarify or complete."""

    text: str
    constraints: list[str] = field(default_factory=list)
    preferences: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "constraints": list(self.constraints),
            "preferences": dict(self.preferences),
        }


@dataclass(frozen=True)
class Clarification:
    """A question Pyxis asks before acting on an underspecified request."""

    question: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "question": self.question,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class TonePolicy:
    """Tone preferences applied to agent-facing responses."""

    calm: bool = True
    concise: bool = True
    supportive: bool = True

    def to_dict(self) -> dict[str, bool]:
        return {
            "calm": self.calm,
            "concise": self.concise,
            "supportive": self.supportive,
        }


@dataclass(frozen=True)
class ResponseStyle:
    """Lightweight response shaping for calm, concise, supportive output."""

    tone: TonePolicy = field(default_factory=TonePolicy)
    empty_response: str = "I need a little more context before I can help well."

    def apply(self, output: str) -> str:
        styled = output.strip()
        if styled:
            return styled
        return self.empty_response

    def to_dict(self) -> dict:
        return {
            "tone": self.tone.to_dict(),
            "empty_response": self.empty_response,
        }


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
    goal: UserGoal | None = None
    intent: Intent | None = None
    constraints: list[str] = field(default_factory=list)
    preferences: dict[str, str] = field(default_factory=dict)
    clarifications: list[Clarification] = field(default_factory=list)
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
            "goal": self.goal.to_dict() if self.goal else None,
            "intent": self.intent.to_dict() if self.intent else None,
            "constraints": list(self.constraints),
            "preferences": dict(self.preferences),
            "clarifications": [
                clarification.to_dict() for clarification in self.clarifications
            ],
            "open_questions": list(self.open_questions),
            "confirmations": list(self.confirmations),
        }

"""Top-level Pyxis facade."""

from __future__ import annotations

from dataclasses import dataclass, field

from pyxis.agent import Agent
from pyxis.compass import Compass
from pyxis.policy import ControlPolicy
from pyxis.session import Session


@dataclass
class Pyxis:
    """Convenience facade for creating sessions around an agent."""

    agent: Agent
    compass: Compass = field(default_factory=Compass)
    policy: ControlPolicy = field(default_factory=ControlPolicy.safe_default)

    def session(self) -> Session:
        return Session(agent=self.agent, compass=self.compass, policy=self.policy)

    def navigate(self, user_input: str):
        return self.session().navigate(user_input)

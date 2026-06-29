"""Pyxis exceptions."""


class PyxisError(Exception):
    """Base error for Pyxis."""


class CheckpointRequired(PyxisError):
    """Raised when an action requires confirmation before it can continue."""


class CheckpointRejected(PyxisError):
    """Raised when a checkpoint is rejected."""


class ToolExecutionError(PyxisError):
    """Raised when a tool fails during execution."""


class ProviderConfigurationError(PyxisError):
    """Raised when a provider is missing required configuration."""


class ProviderRequestError(PyxisError):
    """Raised when a provider request fails."""

"""Pyxis exceptions."""


class PyxisError(Exception):
    """Base error for Pyxis."""


class CheckpointRequired(PyxisError):
    """Raised when an action requires confirmation before it can continue."""


class CheckpointRejected(PyxisError):
    """Raised when a checkpoint is rejected."""


class CheckpointNotFound(PyxisError):
    """Raised when a checkpoint cannot be found."""


class CheckpointNotApproved(PyxisError):
    """Raised when an action is resumed before approval."""


class ToolExecutionError(PyxisError):
    """Raised when a tool fails during execution."""


class ToolValidationError(PyxisError):
    """Raised when a tool call does not match the tool signature."""


class ToolNotFound(PyxisError):
    """Raised when an agent does not have a requested tool."""


class ProviderConfigurationError(PyxisError):
    """Raised when a provider is missing required configuration."""


class ProviderRequestError(PyxisError):
    """Raised when a provider request fails."""


class SnapshotRestoreError(PyxisError):
    """Raised when a session snapshot cannot be restored."""

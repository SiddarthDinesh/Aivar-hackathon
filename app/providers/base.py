from __future__ import annotations

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Common interface for all LLM providers."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a response for the given prompt."""
        raise NotImplementedError

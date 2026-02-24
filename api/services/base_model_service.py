import abc
from typing import Any, Dict, List

class BaseModelService(abc.ABC):
    """
    Abstract base class for all model services.
    Enforces a common interface for training, prediction, persistence, and validation.
    """

    @abc.abstractmethod
    def train(self, *args, **kwargs) -> Any:
        """Train the model with provided data."""
        pass

    @abc.abstractmethod
    def predict(self, *args, **kwargs) -> Any:
        """Make predictions using the trained model."""
        pass

    @abc.abstractmethod
    def load(self, path: str) -> None:
        """Load the model from a file or artifact store."""
        pass

    @abc.abstractmethod
    def save(self, path: str) -> None:
        """Save the model to a file or artifact store."""
        pass

    @abc.abstractmethod
    def validate(self, *args, **kwargs) -> Dict[str, float]:
        """Validate the model and return evaluation metrics."""
        pass

    @abc.abstractmethod
    def promote_to_production(self) -> None:
        """Promote the model to production (e.g., update registry, set as active)."""
        pass

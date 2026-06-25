from abc import ABC, abstractmethod
from datetime import datetime


class CloudProvider(ABC):
    @abstractmethod
    def list_resources(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def fetch_cpu_metrics(self, resource_id: str, start: datetime, end: datetime) -> list[dict]:
        raise NotImplementedError

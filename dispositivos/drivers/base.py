# dispositivos/drivers/base.py
from abc import ABC, abstractmethod

class BaseSurveyDriver(ABC):
    @abstractmethod
    def connect(self) -> None:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    @abstractmethod
    def read_once(self) -> dict:
        ...

    @abstractmethod
    def healthcheck(self) -> dict:
        ...
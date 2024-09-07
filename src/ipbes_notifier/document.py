from pydantic import BaseModel, computed_field
from typing import Literal


class Document(BaseModel):
    symbol: str
    title: dict[Literal["en"], str]

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __str__(self) -> str:
        return (
            f"[{self.symbol}] '{self.title.get('en', '<No english title available>')}'"
        )

    @computed_field
    @property
    def id(self) -> str:
        return f"[{self.symbol}]: {self.title}"

from sqlmodel import Field, Relationship, SQLModel

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ipbes_notifier.subscription import Subscription


class Chat(SQLModel, table=True):
    id: int = Field(primary_key=True)
    subscriptions: list["Subscription"] = Relationship(
        back_populates="chat", sa_relationship_kwargs={"cascade": "delete"}
    )

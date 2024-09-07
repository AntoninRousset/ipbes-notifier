from sqlmodel import Field, Relationship, SQLModel

from typing import TYPE_CHECKING

from ipbes_notifier.chat import Chat

if TYPE_CHECKING:  # pragma: no cover
    from ipbes_notifier.topic import Topic


class Subscription(SQLModel, table=True):
    chat_id: int = Field(foreign_key="chat.id", primary_key=True)
    chat: Chat = Relationship(
        back_populates="subscriptions", sa_relationship_kwargs={"cascade": "delete"}
    )
    topic_name: str = Field(foreign_key="topic.name", primary_key=True)
    topic: "Topic" = Relationship(back_populates="subscriptions")

from collections import defaultdict
import httpx
from sqlmodel import Field, Relationship, SQLModel
from typing import ClassVar
from bs4 import BeautifulSoup

from ipbes_notifier.document import Document
from ipbes_notifier.subscription import Subscription


class Topic(SQLModel, table=True):
    _documents: ClassVar[defaultdict[str, set[Document]]] = defaultdict(set)
    name: str = Field(primary_key=True)
    subscriptions: list[Subscription] = Relationship(back_populates="topic")
    url: str

    @property
    def documents(self):
        return Topic._documents[self.name]

    async def poll(self) -> list[Document]:
        headers = {
            "User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(self.url, headers=headers)
            soup = BeautifulSoup(response.content)

            documents = [
                Document(
                    symbol=card_title.select_one(".field--name-name").text.strip(),
                    title={
                        "en": card_title.select_one(
                            ".field--name-field-document-name"
                        ).text.strip()
                    },
                )
                for card_title in soup.select(".card-title")
            ]

            for document in documents:
                if document not in self.documents:
                    yield document
                    self.documents.add(document)

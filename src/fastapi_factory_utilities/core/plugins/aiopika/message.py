"""Provides the message for the Aiopika plugin."""

from enum import StrEnum, auto
from typing import ClassVar, Generic, TypeVar

from aio_pika.abc import AbstractIncomingMessage, DeliveryMode, HeadersType
from aio_pika.message import Message
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

GenericMessageData = TypeVar("GenericMessageData", bound=BaseModel)


class SenderModel(BaseModel):
    """Sender model."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(description="The name of the sender.")


class MessageTypeEnum(StrEnum):
    """Message type enum."""

    FUNCTIONAL_EVENT = auto()


class AbstractMessage(BaseModel, Generic[GenericMessageData]):
    """Abstract message."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    message_type: MessageTypeEnum = Field(
        description="The type of the message.", default=MessageTypeEnum.FUNCTIONAL_EVENT
    )
    sender: SenderModel = Field(description="The sender of the message.")
    data: GenericMessageData = Field(description="The data of the message.")

    _incoming_message: AbstractIncomingMessage | None = PrivateAttr()
    _headers: HeadersType = PrivateAttr(default_factory=dict)

    def get_headers(self) -> HeadersType:
        """Get the headers of the message."""
        return self._headers

    def set_headers(self, headers: HeadersType) -> None:
        """Set the headers of the message."""
        self._headers = headers

    def set_incoming_message(self, incoming_message: AbstractIncomingMessage) -> None:
        """Set the incoming message."""
        self._incoming_message = incoming_message
        self.set_headers(headers=incoming_message.headers)

    async def ack(self) -> None:
        """Ack the message.

        Raises:
            - ValueError: If the incoming message is not set.
        """
        if self._incoming_message is None:
            raise ValueError("Incoming message is not set.")
        await self._incoming_message.ack(multiple=False)

    async def reject(self, requeue: bool = True) -> None:
        """Reject the message.

        Args:
            requeue (bool): Whether to requeue the message.

        Raises:
            - ValueError: If the incoming message is not set.
        """
        if self._incoming_message is None:
            raise ValueError("Incoming message is not set.")
        await self._incoming_message.reject(requeue=requeue)

    def to_aiopika_message(self) -> Message:
        """Convert the message to an Aiopika message."""
        return Message(
            body=self.model_dump_json().encode("utf-8"),
            headers=self.get_headers(),
            content_type="application/json",
            content_encoding="utf-8",
            delivery_mode=DeliveryMode.PERSISTENT,
            priority=0,
        )

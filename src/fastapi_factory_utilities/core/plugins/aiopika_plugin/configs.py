"""Aiopika plugin credentials config."""

from typing import Annotated, ClassVar

from pydantic import BaseModel, ConfigDict, Field, UrlConstraints
from pydantic_core import Url


class RabbitMQCredentialsConfig(BaseModel):
    """Provides the configuration model for the Aiopika plugin.

    https://docs.aio-pika.com/#aio-pika-connect-robust-function-and-aio-pika-robustconnection-class-specific

    Possible query parameters for the AMQP URL:
        name (str url encoded) - A string that will be visible in the RabbitMQ management console
        and in the server logs, convenient for diagnostics.
        cafile (str) - Path to Certificate Authority file
        capath (str) - Path to Certificate Authority directory
        cadata (str url encoded) - URL encoded CA certificate content
        keyfile (str) - Path to client ssl private key file
        certfile (str) - Path to client ssl certificate file
        no_verify_ssl - No verify server SSL certificates. 0 by default and means False other value means True.
        heartbeat (int-like) - interval in seconds between AMQP heartbeat packets. 0 disables this feature.
        reconnect_interval (float-like) - is the period in seconds, not more often than the attempts
        to re-establish the connection will take place.
        fail_fast (true/yes/y/enable/on/enabled/1 means True, otherwise False) - special behavior
        for the start connection attempt, if it fails, all other attempts stops
        and an exception will be thrown at the connection stage. Enabled by default, if you are sure you need
        to disable this feature, be ensures for the passed URL is really working.
        Otherwise, your program will go into endless reconnection attempts that can not be successed.

    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    amqp_url: Annotated[Url, UrlConstraints(allowed_schemes=["amqp", "amqps"])] = Field(description="The AMQP URL.")

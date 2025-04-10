from typing import TypedDict, Optional


class VigilantUserConfig(TypedDict):
    """
    VigilantUserConfig is used to configure the Vigilant global instance when it is created.

    `name` and `token` are required, the other fields are optional.
    """
    name: str
    token: str
    endpoint: Optional[str]
    insecure: Optional[bool]
    passthrough: Optional[bool]
    autocapture: Optional[bool]
    noop: Optional[bool]

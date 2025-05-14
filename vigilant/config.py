from typing import Optional, Dict


class VigilantUserConfig:
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

    def __init__(
        self,
        name: str,
        token: str,
        endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        passthrough: Optional[bool] = None,
        autocapture: Optional[bool] = None,
        noop: Optional[bool] = None,
        attributes: Optional[Dict[str, str]] = None,
    ):
        self.name = name
        self.token = token
        self.endpoint = endpoint
        self.insecure = insecure
        self.passthrough = passthrough
        self.autocapture = autocapture
        self.noop = noop
        self.attributes = attributes

from app.enums.base import BaseStrEnum

__all__ = ["AuthMethodEnum", "SecurityPolicyEnum"]


class AuthMethodEnum(BaseStrEnum):
    """
    Enum representing authentication methods for OPC servers.
    """

    ANONYMOUS = "anonymous"
    USERNAME = "username"


class SecurityPolicyEnum(BaseStrEnum):
    """
    Enum representing security policies for OPC servers.
    """

    # Recommended security policies
    AES256_SHA256_RSAPSS = "Aes256_Sha256_RsaPss"
    AES128_SHA256_RSAOAEP = "Aes128_Sha256_RsaOaep"
    BASIC256_SHA256 = "Basic256Sha256"

    # Without security encryption
    NONE = "None"

    # Legacy security policies
    BASIC256 = "Basic256"
    BASIC128_RSA15 = "Basic128Rsa15"

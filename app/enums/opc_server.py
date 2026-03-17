from app.enums.base import BaseStrEnum

__all__ = ["AuthMethodEnum", "SecurityPolicyEnum"]


class AuthMethodEnum(BaseStrEnum):
    """
    Enum representing authentication methods for OPC servers.
    """

    anonymous = "anonymous"
    username = "username"


class SecurityPolicyEnum(BaseStrEnum):
    """
    Enum representing security policies for OPC servers.
    """

    # Recommended security policies
    aes256_sha256_rsapss = "Aes256_Sha256_RsaPss"
    aes128_sha256_rsaoaep = "Aes128_Sha256_RsaOaep"
    basic256_sha256 = "Basic256Sha256"

    # Without security encryption
    none = "None"
    # Legacy security policies
    basic256 = "Basic256"
    basic128_rsa15 = "Basic128Rsa15"

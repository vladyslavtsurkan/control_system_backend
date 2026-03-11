from argon2 import Type

# Verification code settings
DEFAULT_CODE_LENGTH = 6

# Pagination settings
PAGINATION_PER_PAGE = 10

# API key settings
API_KEY_LENGTH = 40
API_KEY_PREFIX = "sk_live_"

# Hashing settings for CollectorHasher
COLLECTOR_HASHER_TIME_COST = 1
COLLECTOR_HASHER_MEMORY_COST = 4096
COLLECTOR_HASHER_PARALLELISM = 1
COLLECTOR_HASHER_TYPE = Type.ID

# WebSocket settings
WS_PING_INTERVAL = 30  # seconds
WS_TICKET_TTL = 30  # seconds — single-use ticket lifetime

# Alerting settings
DEFAULT_NO_DATA_TIMEOUT_SECONDS = 300  # 5 minutes

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

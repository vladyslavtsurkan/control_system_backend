from argon2 import Type

# Verification code settings
DEFAULT_CODE_LENGTH = 6

# Pagination settings
PAGINATION_PER_PAGE = 10
PAGINATION_MAX_PER_PAGE = 100
PAGINATION_DEFAULT_OFFSET = 0

# Readings general settings
READINGS_MAX_HOURS_WINDOW = 25

# Readings query defaults
READINGS_DEFAULT_RANGE_HOURS = 24
READINGS_DEFAULT_SAMPLE_EVERY = 1

# Sensor prefetch defaults
SENSOR_PREFETCH_DEFAULT_WINDOW_MINUTES = 15
SENSOR_PREFETCH_MAX_WINDOW_MINUTES = 180

# Service-level large fetch cap used for tenant-wide fan-out queries
SERVICE_INTERNAL_FETCH_LIMIT = 10000

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
ALERT_UPDATE_THROTTLE_SECONDS = 120  # emit update events at most once per 2 minutes per rule
ALERT_RESOLVE_CONSECUTIVE_OK_READINGS = 10  # for NO_DATA auto-resolve

"""Constants for the Domyos Rower integration."""

DOMAIN = "domyos_rower"

POLL_INTERVAL = 0.3  # seconds between status requests / command checks
ACK_TIMEOUT = 0.3  # max wait for an answer during the Domyos init sequence
STALE_TIMEOUT = 15.0  # Domyos mode: no status packet for this long -> drop
PROP_NO_DATA_TIMEOUT = 6.0  # Domyos mode: never answered after init -> try FTMS
FTMS_CMD_TIMEOUT = 1.0  # wait for a Control Point indication
FTMS_STROKE_IDLE = 3.0  # no new stroke for this long -> cadence/speed/power = 0
RETRY_DELAY = 20.0  # pause after a failed/finished session

STATUS_DISABLED = "disabled"
STATUS_WAITING = "waiting"
STATUS_CONNECTING = "connecting"
STATUS_CONNECTED = "connected"
STATUS_ERROR = "error"
STATUSES = [STATUS_DISABLED, STATUS_WAITING, STATUS_CONNECTING, STATUS_CONNECTED, STATUS_ERROR]

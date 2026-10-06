"""Constants for the Domyos Rower integration."""

DOMAIN = "domyos_rower"

POLL_INTERVAL = 0.3  # seconds between status requests / command checks
ACK_TIMEOUT = 0.3  # max wait for an answer during the Domyos init sequence
STALE_TIMEOUT = 15.0  # Domyos mode: no status packet for this long -> drop
PROP_NO_DATA_TIMEOUT = 6.0  # Domyos mode: never answered after init -> try FTMS
FTMS_CMD_TIMEOUT = 1.0  # wait for a Control Point indication
FTMS_STROKE_IDLE = 3.0  # no new stroke for this long -> cadence/speed/power = 0
# Pause before the next connection attempt: 1st retry fast (e.g. link lost mid-workout),
# then back off so a rower that keeps refusing doesn't keep the proxy from scanning.
RETRY_DELAYS = (3.0, 10.0, 20.0, 40.0, 60.0, 120.0)
MIN_GOOD_SESSION = 10.0  # a connected session at least this long resets the back-off

STATUS_DISABLED = "disabled"
STATUS_WAITING = "waiting"
STATUS_CONNECTING = "connecting"
STATUS_CONNECTED = "connected"
STATUS_ERROR = "error"
STATUSES = [STATUS_DISABLED, STATUS_WAITING, STATUS_CONNECTING, STATUS_CONNECTED, STATUS_ERROR]

DISPLAY_INTERVAL = 1.0  # Domyos mode: console screen refreshed once per second (like QZ)
DISTANCE_SCALE_MIN = 0.5
DISTANCE_SCALE_MAX = 2.0

# --- session recording / export
SAMPLE_INTERVAL = 1.0  # seconds between recorded samples
EVENT_SESSION_SAVED = "domyos_rower_session_saved"

CONF_STRAVA = "strava"
CONF_OUTPUT_DIR = "output_dir"
CONF_SPORT_TYPE = "sport_type"
CONF_GPX_LAT = "gpx_latitude"
CONF_GPX_LON = "gpx_longitude"
SPORT_TYPES = ["Rowing", "VirtualRow"]
DEFAULT_SPORT_TYPE = "Rowing"

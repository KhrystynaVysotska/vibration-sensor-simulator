import os

DEVICE_ID = os.environ.get('DEVICE_ID')
REGION = os.environ.get('REGION')
PROJECT_ID = os.environ.get('PROJECT_ID')
REGISTRY_ID = os.environ.get('REGISTRY_ID')
PRIVATE_KEY_FILE_PATH = os.environ.get('PRIVATE_KEY_FILE_PATH')
CERTIFICATES_FILE_PATH = "./roots.pem"

STATE_TOPIC = "state"
DEFAULT_TOPIC = "events"
LOGS_TOPIC = "events/logs"
TELEMETRY_TOPIC = "events/telemetry"


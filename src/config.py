import os
from dotenv import load_dotenv

load_dotenv()

MQTT_HOST = os.getenv("MQTT_HOST", "0.0.0.0")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", "8080"))

LOG_PACKET_TIMES = os.getenv("LOG_PACKET_TIMES", "1") == "1"
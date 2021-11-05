import time
import random
import datetime

from configs.gcp_configs import *
from configs.mqtt_configs import *

import paho.mqtt.client as mqtt
from paho.mqtt.client import ssl
from jwt_generator import create_jwt
from vibrations_generator import generate_vibrations_data

should_backoff = True
minimum_backoff_time = 1
maximum_backoff_time = 4


def error_str(rc):
    """Convert a Paho error to a human readable string."""
    return "{}: {}".format(rc, mqtt.error_string(rc))


def on_connect(unused_client, unused_userdata, unused_flags, rc):
    """Callback for when a device connects."""
    print("on_connect", mqtt.connack_string(rc))

    global should_backoff
    global minimum_backoff_time

    # After a successful connect, reset backoff time and stop backing off.
    should_backoff = False
    minimum_backoff_time = 1


def on_disconnect(unused_client, unused_userdata, rc):
    """Paho callback for when a device disconnects."""
    print("on_disconnect", error_str(rc))

    # Since a disconnect occurred, the next loop iteration will wait with
    # exponential backoff.
    global should_backoff
    should_backoff = True


def on_publish(unused_client, unused_userdata, unused_mid):
    """Paho callback when a message is sent to the broker."""
    print("on_publish")


def on_message(unused_client, unused_userdata, message):
    """Callback when the device receives a message on a subscription."""
    payload = str(message.payload.decode("utf-8"))
    print(
        "Received message '{}' on topic '{}' with Qos {}".format(
            payload, message.topic, str(message.qos)
        )
    )


def get_client(
        project_id,
        cloud_region,
        registry_id,
        device_id,
        private_key_file,
        algorithm,
        ca_certs,
        mqtt_bridge_hostname,
        mqtt_bridge_port,
        jwt_expires_minutes
):
    """Create our MQTT client. The client_id is a unique string that identifies
    this device. For Google Cloud IoT Core, it must be in the format below."""
    client_id = "projects/{}/locations/{}/registries/{}/devices/{}".format(
        project_id, cloud_region, registry_id, device_id
    )
    print("Device client_id is '{}'".format(client_id))

    client = mqtt.Client(client_id=client_id)

    # With Google Cloud IoT Core, the username field is ignored, and the
    # password field is used to transmit a JWT to authorize the device.
    client.username_pw_set(
        username="unused", password=create_jwt(project_id, private_key_file, algorithm, jwt_expires_minutes)
    )

    # Enable SSL/TLS support.
    client.tls_set(ca_certs=ca_certs, tls_version=ssl.PROTOCOL_TLSv1_2)

    # Register message callbacks. https://eclipse.org/paho/clients/python/docs/
    # describes additional callbacks that Paho supports. In this example, the
    # callbacks just print to standard out.
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Connect to the Google MQTT bridge.
    client.connect(mqtt_bridge_hostname, mqtt_bridge_port)

    # This is the topic that the device will receive configuration updates on.
    mqtt_config_topic = "/devices/{}/config".format(device_id)

    # Subscribe to the config topic.
    client.subscribe(mqtt_config_topic, qos=0)
    # Subscribe to the commands topic, QoS 1 enables message acknowledgement.
    print("Subscribing to {}".format(mqtt_config_topic))

    # The topic that the device will receive commands on.
    mqtt_command_topic = "/devices/{}/commands/#".format(device_id)

    # Subscribe to the commands topic, QoS 1 enables message acknowledgement.
    print("Subscribing to {}".format(mqtt_command_topic))
    client.subscribe(mqtt_command_topic, qos=0)

    return client


def publish_data(
        jwt_expires_minutes,
        project_id,
        cloud_region,
        registry_id,
        device_id,
        private_key_file,
        algorithm,
        ca_certs,
        mqtt_bridge_hostname,
        mqtt_bridge_port
):
    jwt_iat = datetime.datetime.utcnow()
    jwt_exp_seconds = jwt_expires_minutes * 60

    client = get_client(
        project_id,
        cloud_region,
        registry_id,
        device_id,
        private_key_file,
        algorithm,
        ca_certs,
        mqtt_bridge_hostname,
        mqtt_bridge_port,
        jwt_expires_minutes
    )

    global minimum_backoff_time

    # Publish num_messages messages to the MQTT bridge once per second.
    while True:
        # Process network events
        client.loop()

        # Wait if backoff is required.
        if should_backoff:
            if minimum_backoff_time > maximum_backoff_time:
                print("Exceeded maximum backoff time. Giving up.")
                break

            delay = minimum_backoff_time + random.randint(0, 1000) / 1000.0
            print("Waiting for {} before reconnecting.".format(delay))
            time.sleep(delay)
            minimum_backoff_time *= 2
            client.connect(mqtt_bridge_hostname, mqtt_bridge_port)

        seconds_since_issue = (datetime.datetime.utcnow() - jwt_iat).seconds
        if seconds_since_issue > jwt_exp_seconds:
            print("Refreshing token after {}s".format(seconds_since_issue))
            jwt_iat = datetime.datetime.utcnow()
            client.loop()
            client.disconnect()
            client = get_client(
                project_id,
                cloud_region,
                registry_id,
                device_id,
                private_key_file,
                algorithm,
                ca_certs,
                mqtt_bridge_hostname,
                mqtt_bridge_port,
                jwt_expires_minutes
            )
        # Publish "payload" to the MQTT topic. qos=1 means at least once
        # delivery. Cloud IoT Core also supports qos=0 for at most once
        # delivery.
        payload = generate_vibrations_data(device_id)
        client.publish("/devices/{}/{}".format(device_id, STATE_TOPIC), f"{device_id} STARTED SENDING DATA", qos=1)
        time.sleep(1)

        client.publish("/devices/{}/{}".format(device_id, TELEMETRY_TOPIC), payload, qos=1)

        time.sleep(1)
        client.publish("/devices/{}/{}".format(device_id, STATE_TOPIC), f"{device_id} SLEEP", qos=1)

        # Send events every 5 seconds. State should not be updated as often
        time.sleep(5)


if __name__ == '__main__':
    publish_data(
        jwt_expires_minutes=20,
        project_id=PROJECT_ID,
        cloud_region=REGION,
        registry_id=REGISTRY_ID,
        device_id=DEVICE_ID,
        private_key_file=PRIVATE_KEY_FILE_PATH,
        algorithm="RS256",
        ca_certs=CERTIFICATES_FILE_PATH,
        mqtt_bridge_hostname=MQTT_BRIDGE_HOSTNAME,
        mqtt_bridge_port=MQTT_BRIDGE_PORT
    )

import json
import random


def generate_vibrations_data(device_id):
    x = random.sample(range(-512, 512), 50)
    y = random.sample(range(-512, 512), 50)
    z = random.sample(range(-512, 512), 50)

    vibrations_data = {"id": device_id, "x": x, "y": y, "z": z}

    return json.dumps(vibrations_data)

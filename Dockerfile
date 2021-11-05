FROM python:3.8-slim-buster

WORKDIR /app
COPY . .

RUN pip3 install -r requirements.txt

ENV REGION europe-west1
ENV PROJECT_ID big-data-camp-331210
ENV REGISTRY_ID vibration-device-registry

CMD ["python", "./mqtt_client.py"]
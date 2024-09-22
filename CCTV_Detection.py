import cv2
import paho.mqtt.client as mqtt
import time
import requests
import os

# Pushover setup
pushover_user_key = "u4woqxa166nqfehrj7kfz7nrridksw"
pushover_api_token = "anraeqraynw9h96uhj8qw5ayjrz1yq"
pushover_url = "https://api.pushover.net/1/messages.json"

# MQTT setup
broker = "broker.hivemq.com"  # Free public broker
port = 1883
topic = "motion/detection"
message = "Motion detected"
client_id = "Pa2004;()"

# MQTT callback functions
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
    else:
        print(f"Failed to connect, return code {rc}")

def on_publish(client, userdata, mid):
    print(f"Message published (mid={mid})")

# Function to send MQTT message
def send_mqtt_message(broker, port, topic, message, client_id):
    client = mqtt.Client(client_id)
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.connect(broker, port)
    client.loop_start()
    result = client.publish(topic, message, qos=1)
    status = result.rc
    if status == 0:
        print(f"Sent `{message}` to topic `{topic}`")
    else:
        print(f"Failed to send message to topic `{topic}`")
    client.loop_stop()
    client.disconnect()

# Function to send Pushover notification with an image
def send_pushover_notification(message, image_path=None):
    payload = {
        "token": pushover_api_token,
        "user": pushover_user_key,
        "message": message,
        "title": "Motion Alert"
    }
    files = {'attachment': open(image_path, 'rb')} if image_path else None
    response = requests.post(pushover_url, data=payload, files=files)
    if response.status_code == 200:
        print("Pushover notification sent successfully")
    else:
        print(f"Failed to send Pushover notification: {response.text}")

# Initialize video capture
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open video stream")
    exit()

ret, frame1 = cap.read()
if not ret:
    print("Error: Failed to read the frame1")
    cap.release()
    exit()

ret, frame2 = cap.read()
if not ret:
    print("Error: Failed to read the frame2")
    cap.release()
    exit()

motion_detected = False

while cap.isOpened():
    diff = cv2.absdiff(frame1, frame2)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
    dilated = cv2.dilate(thresh, None, iterations=3)
    contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    current_motion_detected = False
    for contour in contours:
        if cv2.contourArea(contour) < 500:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        cv2.rectangle(frame1, (x, y), (x+w, y+h), (0, 255, 0), 2)
        current_motion_detected = True

    if current_motion_detected and not motion_detected:
        motion_detected = True
        print("Motion detected!")

        # Save the frame as an image
        image_path = "motion_detected.jpg"
        cv2.imwrite(image_path, frame1)
        print(f"Frame saved to {image_path}")

        # Send the notifications
        send_mqtt_message(broker, port, topic, message, client_id)
        send_pushover_notification(message, image_path)

        # Remove the image file after sending
        os.remove(image_path)
        print("Image file removed after sending")

    elif not current_motion_detected:
        motion_detected = False

    cv2.imshow("feed", frame1)
    frame1 = frame2
    ret, frame2 = cap.read()
    if not ret:
        print("Error: Failed to read the frame")
        break

    if cv2.waitKey(1) & 0xFF == ord('e'):
        break

cap.release()
cv2.destroyAllWindows()


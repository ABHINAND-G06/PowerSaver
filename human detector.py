import cv2
import serial
import time
from ultralytics import YOLO

model = YOLO("yolov8n.pt")

ser = serial.serial_for_url(
    "rfc2217://localhost:4000",
    baudrate=115200,
    timeout=1
)

print("Connected to Wokwi STM32")

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Could not open camera")
    ser.close()
    exit()

# Timer duration in seconds
TIMEOUT = 10

# Appliances start ON
appliances_on = True
last_person_time = time.time()

# Tell STM32 to turn appliances ON initially
ser.write(b"OCCUPANCY:1\n")
print("System started -> Appliances ON")

while True:

    ret, frame = cap.read()

    if not ret:
        print("Camera error")
        break

    results = model(frame, verbose=False)

    person_detected = False

    for result in results:
        for box in result.boxes:

            class_id = int(box.cls[0])
            confidence = float(box.conf[0])

            # YOLO class 0 = person
            if class_id == 0 and confidence > 0.5:

                person_detected = True

                x1, y1, x2, y2 = map(int, box.xyxy[0])

                # Shrink displayed bounding box by 10%
                w = x2 - x1
                h = y2 - y1

                x1 += int(w * 0.05)
                x2 -= int(w * 0.05)
                y1 += int(h * 0.05)
                y2 -= int(h * 0.05)

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"Person {confidence:.2f}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

    # --------------------------------
    # PERSON DETECTED
    # --------------------------------

    if person_detected:

        # Reset inactivity timer
        last_person_time = time.time()

        # If appliances were OFF, turn them ON
        if not appliances_on:

            ser.write(b"1")

            appliances_on = True

            print("Person detected -> Appliances ON")

    # --------------------------------
    # NO PERSON
    # --------------------------------

    else:

        elapsed_time = time.time() - last_person_time

        remaining_time = TIMEOUT - elapsed_time

        # Timer expired
        if elapsed_time >= TIMEOUT and appliances_on:

            ser.write(b"0")

            appliances_on = False

            print("Timer expired -> Appliances OFF")

    # --------------------------------
    # DISPLAY STATUS
    # --------------------------------

    if appliances_on:
        state = "ON"
    else:
        state = "OFF"

    cv2.putText(
        frame,
        f"Appliances: {state}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2
    )

    # Show countdown when appliances are ON
    if not person_detected and appliances_on:

        remaining = max(0, int(TIMEOUT - (time.time() - last_person_time)))

        cv2.putText(
            frame,
            f"Shutdown in: {remaining}s",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

    elif person_detected:

        cv2.putText(
            frame,
            "Person detected - Timer reset",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

    else:

        cv2.putText(
            frame,
            "No person - Appliances OFF",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

    cv2.imshow("AI Power Saving System", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
ser.close()
cv2.destroyAllWindows()

print("Program stopped")
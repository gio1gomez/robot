from pathlib import Path
import time
import threading

import cv2
import serial
from flask import Flask, Response, render_template, request, jsonify
from ultralytics import YOLO

# =========================
# CONFIGURACION
# =========================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "best_float32.tflite"

CAMERA_INDEX = 0
CONFIDENCE_THRESHOLD = 0.50

FRAME_WIDTH = 640
FRAME_HEIGHT = 480

MODEL_IMG_SIZE = 320

SERIAL_PORT = "/dev/serial0"
SERIAL_BAUD = 115200

FIRE_FRAMES_TO_ACTIVATE = 1
NO_FIRE_FRAMES_TO_CLEAR = 10

INFER_EVERY_N_FRAMES = 2

# =========================
# FLASK
# =========================

app = Flask(__name__)

latest_jpeg = None
frame_lock = threading.Lock()

ser = None
serial_lock = threading.Lock()
fire_state_sent = False

# =========================
# UART
# =========================

def open_uart():
    global ser

    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
        time.sleep(2)
        print(f"UART abierta en {SERIAL_PORT} a {SERIAL_BAUD}")
        send_uart("STOP")
    except Exception as e:
        ser = None
        print("No se pudo abrir UART")
        print("Error:", e)


def send_uart(cmd):
    global ser

    cmd = cmd.strip().upper()

    with serial_lock:
        if ser is None or not ser.is_open:
            print(f"[UART NO DISPONIBLE] {cmd}")
            return False

        try:
            ser.write((cmd + "\n").encode("utf-8"))
            print(f"[UART] Enviado: {cmd}")
            return True
        except Exception as e:
            print("Error enviando UART:", e)
            return False

# =========================
# CAMARA + MODELO
# =========================

def draw_detections(frame, detections):
    for det in detections:
        x1 = det["x1"]
        y1 = det["y1"]
        x2 = det["x2"]
        y2 = det["y2"]
        confidence = det["confidence"]

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)

        text = f"FIRE {confidence * 100:.1f}%"
        cv2.putText(
            frame,
            text,
            (x1, max(y1 - 10, 30)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
            cv2.LINE_AA
        )


def camera_loop():
    global latest_jpeg
    global fire_state_sent

    if not MODEL_PATH.exists():
        print("No se encontro el modelo.")
        print(f"Ruta buscada: {MODEL_PATH}")
        print("Archivos en la carpeta:")
        for file in BASE_DIR.iterdir():
            print(" -", file.name)
        return

    print("Cargando modelo YOLO TFLite...")
    print(f"Modelo usado: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))
    print("Modelo cargado correctamente.")
    print("Clases:", model.names)

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)

    if not cap.isOpened():
        print(f"No se pudo abrir la camara con indice {CAMERA_INDEX}.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    print("Camara iniciada para pagina web.")

    fire_counter = 0
    no_fire_counter = 0
    frame_count = 0

    last_detections = []
    last_fire_detected = False
    last_best_confidence = 0.0

    while True:
        ret, frame = cap.read()

        if not ret:
            print("No se pudo leer la camara.")
            time.sleep(0.1)
            continue

        frame_count += 1

        do_inference = frame_count % INFER_EVERY_N_FRAMES == 0

        if do_inference:
            results = model.predict(
                source=frame,
                conf=CONFIDENCE_THRESHOLD,
                imgsz=MODEL_IMG_SIZE,
                verbose=False
            )

            fire_detected = False
            best_confidence = 0.0
            detections = []

            for result in results:
                boxes = result.boxes

                if boxes is None:
                    continue

                for box in boxes:
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    label = str(model.names[class_id]).lower()

                    if label not in ["fire", "fuego"]:
                        continue

                    fire_detected = True
                    best_confidence = max(best_confidence, confidence)

                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)

                    detections.append({
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "confidence": confidence,
                        "label": label
                    })

            last_detections = detections
            last_fire_detected = fire_detected
            last_best_confidence = best_confidence

        fire_detected = last_fire_detected
        best_confidence = last_best_confidence

        draw_detections(frame, last_detections)

        # =========================
        # UART CUANDO DETECTA FUEGO
        # =========================

        if fire_detected:
            fire_counter += 1
            no_fire_counter = 0

            if fire_counter >= FIRE_FRAMES_TO_ACTIVATE and not fire_state_sent:
                send_uart("FIRE_DETECTED")
                fire_state_sent = True

        else:
            no_fire_counter += 1
            fire_counter = 0

            if no_fire_counter >= NO_FIRE_FRAMES_TO_CLEAR and fire_state_sent:
                send_uart("FIRE_CLEARED")
                fire_state_sent = False

        # =========================
        # TEXTO EN VIDEO
        # =========================

        if fire_detected:
            status_text = f"FUEGO DETECTADO {best_confidence * 100:.1f}%"
            status_color = (0, 0, 255)
        else:
            status_text = "SIN FUEGO"
            status_color = (0, 255, 0)

        cv2.putText(
            frame,
            status_text,
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.1,
            status_color,
            3,
            cv2.LINE_AA
        )

        ok, buffer = cv2.imencode(
            ".jpg",
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, 70]
        )

        if ok:
            with frame_lock:
                latest_jpeg = buffer.tobytes()

        time.sleep(0.01)

# =========================
# RUTAS WEB
# =========================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    def generate():
        global latest_jpeg

        while True:
            with frame_lock:
                frame = latest_jpeg

            if frame is None:
                time.sleep(0.05)
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )

            time.sleep(0.03)

    return Response(
        generate(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/command", methods=["POST"])
def command():
    data = request.get_json(silent=True) or {}
    cmd = str(data.get("cmd", "")).strip().upper()

    allowed_commands = {
        "FWD",
        "BACK",
        "LEFT",
        "RIGHT",
        "STOP",
        "SERVO_SWEEP_ON",
        "SERVO_SWEEP_OFF",
        "PUMP_ON",
        "PUMP_OFF"
    }

    if cmd not in allowed_commands:
        return jsonify({
            "ok": False,
            "message": f"Comando no permitido: {cmd}"
        }), 400

    print(f"[WEB] Comando recibido: {cmd}")
    ok = send_uart(cmd)

    return jsonify({
        "ok": ok,
        "message": f"Comando enviado: {cmd}" if ok else f"UART no disponible: {cmd}"
    })

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    open_uart()

    t = threading.Thread(target=camera_loop, daemon=True)
    t.start()

    print("Servidor web iniciado.")
    print("Abre en tu navegador:")
    print("http://10.126.44.8:5000")

    app.run(host="0.0.0.0", port=5000, debug=False)
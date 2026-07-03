from pathlib import Path

import cv2
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from sensor_msgs.msg import CompressedImage
from ultralytics import YOLO


class DetectorNode(Node):
    def __init__(self):
        super().__init__('detector_node')

        self.model_path = self.declare_parameter(
            'model_path',
            '/root/prorob/best_float32.tflite'
        ).value
        self.camera_index = int(self.declare_parameter('camera_index', 0).value)
        self.confidence_threshold = float(self.declare_parameter('confidence_threshold', 0.50).value)
        self.model_img_size = int(self.declare_parameter('model_img_size', 320).value)
        self.infer_every_n_frames = int(self.declare_parameter('infer_every_n_frames', 2).value)

        self.fire_frames_to_activate = int(self.declare_parameter('fire_frames_to_activate', 1).value)
        self.no_fire_frames_to_clear = int(self.declare_parameter('no_fire_frames_to_clear', 10).value)

        self.fire_pub = self.create_publisher(Bool, '/fire_detected', 10)
        self.image_pub = self.create_publisher(CompressedImage, '/camera/fire/image_jpeg', 10)

        if not Path(self.model_path).exists():
            raise FileNotFoundError(f'No se encontro el modelo: {self.model_path}')

        self.get_logger().info(f'Cargando modelo: {self.model_path}')
        self.model = YOLO(str(self.model_path))
        self.get_logger().info(f'Modelo cargado. Clases: {self.model.names}')

        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not self.cap.isOpened():
            self.get_logger().error(f'No se pudo abrir la camara {self.camera_index}')

        self.frame_count = 0
        self.fire_counter = 0
        self.no_fire_counter = 0
        self.fire_state = False

        self.last_detections = []
        self.last_fire_detected = False
        self.last_best_confidence = 0.0

        self.timer = self.create_timer(0.03, self.loop)
        self.get_logger().info('Detector node iniciado')

    def draw_detections(self, frame):
        for det in self.last_detections:
            x1, y1, x2, y2 = det['box']
            conf = det['confidence']

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
            cv2.putText(
                frame,
                f'FIRE {conf * 100:.1f}%',
                (x1, max(y1 - 10, 30)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
                cv2.LINE_AA
            )

    def loop(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        self.frame_count += 1

        if self.frame_count % self.infer_every_n_frames == 0:
            results = self.model.predict(
                source=frame,
                conf=self.confidence_threshold,
                imgsz=self.model_img_size,
                verbose=False
            )

            fire_detected = False
            best_confidence = 0.0
            detections = []

            for result in results:
                if result.boxes is None:
                    continue

                for box in result.boxes:
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    label = str(self.model.names[class_id]).lower()

                    if label not in ['fire', 'fuego']:
                        continue

                    fire_detected = True
                    best_confidence = max(best_confidence, confidence)

                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    detections.append({
                        'box': (x1, y1, x2, y2),
                        'confidence': confidence,
                        'label': label
                    })

            self.last_detections = detections
            self.last_fire_detected = fire_detected
            self.last_best_confidence = best_confidence

        fire_detected = self.last_fire_detected

        if fire_detected:
            self.fire_counter += 1
            self.no_fire_counter = 0

            if self.fire_counter >= self.fire_frames_to_activate and not self.fire_state:
                self.fire_state = True
                self.fire_pub.publish(Bool(data=True))
                self.get_logger().info('Publicado /fire_detected: True')
        else:
            self.no_fire_counter += 1
            self.fire_counter = 0

            if self.no_fire_counter >= self.no_fire_frames_to_clear and self.fire_state:
                self.fire_state = False
                self.fire_pub.publish(Bool(data=False))
                self.get_logger().info('Publicado /fire_detected: False')

        self.draw_detections(frame)

        if self.fire_state:
            text = f'FUEGO DETECTADO {self.last_best_confidence * 100:.1f}%'
            color = (0, 0, 255)
        else:
            text = 'SIN FUEGO'
            color = (0, 255, 0)

        cv2.putText(frame, text, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.1, color, 3, cv2.LINE_AA)

        ok, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if ok:
            msg = CompressedImage()
            msg.format = 'jpeg'
            msg.data = buffer.tobytes()
            self.image_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = DetectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

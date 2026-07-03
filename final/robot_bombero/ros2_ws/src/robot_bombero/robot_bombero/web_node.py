import time
import threading

from flask import Flask, Response, render_template, request, jsonify

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import CompressedImage


class WebNode(Node):
    def __init__(self):
        super().__init__('web_node')

        self.template_folder = self.declare_parameter(
            'template_folder',
            '/root/prorob/templates'
        ).value

        self.latest_jpeg = None
        self.cmd_pub = self.create_publisher(String, '/robot_command', 10)

        self.create_subscription(
            CompressedImage,
            '/camera/fire/image_jpeg',
            self.image_callback,
            10
        )

        self.app = Flask(__name__, template_folder=self.template_folder)
        self.setup_routes()

        threading.Thread(target=self.run_flask, daemon=True).start()
        self.get_logger().info('Web node iniciado')

    def image_callback(self, msg):
        self.latest_jpeg = bytes(msg.data)

    def setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template('index.html')

        @self.app.route('/video_feed')
        def video_feed():
            def generate():
                while True:
                    if self.latest_jpeg is None:
                        time.sleep(0.05)
                        continue

                    yield (
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' +
                        self.latest_jpeg +
                        b'\r\n'
                    )
                    time.sleep(0.03)

            return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

        @self.app.route('/command', methods=['POST'])
        def command():
            data = request.get_json(silent=True) or {}
            cmd = str(data.get('cmd', '')).strip().upper()

            allowed_commands = {
                'FWD',
                'BACK',
                'LEFT',
                'RIGHT',
                'STOP',
                'SERVO_SWEEP_ON',
                'SERVO_SWEEP_OFF',
                'PUMP_ON',
                'PUMP_OFF'
            }

            if cmd not in allowed_commands:
                return jsonify({
                    'ok': False,
                    'message': f'Comando no permitido: {cmd}'
                }), 400

            self.cmd_pub.publish(String(data=cmd))
            self.get_logger().info(f'Publicado /robot_command: {cmd}')

            return jsonify({
                'ok': True,
                'message': f'Comando publicado: {cmd}'
            })

    def run_flask(self):
        self.app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)


def main(args=None):
    rclpy.init(args=args)
    node = WebNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

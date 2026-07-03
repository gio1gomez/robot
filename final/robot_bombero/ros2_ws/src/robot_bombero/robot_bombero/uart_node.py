import time
import serial

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool


class UartNode(Node):
    def __init__(self):
        super().__init__('uart_node')

        self.port = self.declare_parameter('serial_port', '/dev/serial0').value
        self.baud = int(self.declare_parameter('serial_baud', 115200).value)

        self.ser = None
        self.last_fire_state = False

        self.create_subscription(String, '/robot_command', self.command_callback, 10)
        self.create_subscription(Bool, '/fire_detected', self.fire_callback, 10)

        self.open_uart()
        self.get_logger().info('UART node iniciado')

    def open_uart(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            time.sleep(2)
            self.send_uart('STOP')
            self.get_logger().info(f'UART abierta en {self.port} a {self.baud}')
        except Exception as e:
            self.ser = None
            self.get_logger().error(f'No se pudo abrir UART: {e}')

    def send_uart(self, cmd: str):
        cmd = cmd.strip().upper()

        if self.ser is None or not self.ser.is_open:
            self.get_logger().warn(f'UART no disponible para comando: {cmd}')
            return

        try:
            self.ser.write((cmd + '\n').encode('utf-8'))
            self.get_logger().info(f'UART enviado: {cmd}')
        except Exception as e:
            self.get_logger().error(f'Error enviando UART: {e}')

    def command_callback(self, msg):
        self.send_uart(msg.data)

    def fire_callback(self, msg):
        if msg.data and not self.last_fire_state:
            self.send_uart('FIRE_DETECTED')
            self.last_fire_state = True

        elif not msg.data and self.last_fire_state:
            self.send_uart('FIRE_CLEARED')
            self.last_fire_state = False


def main(args=None):
    rclpy.init(args=args)
    node = UartNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

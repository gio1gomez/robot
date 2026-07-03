import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool


class CommandNode(Node):
    def __init__(self):
        super().__init__('command_node')

        self.create_subscription(String, '/robot_command', self.command_callback, 10)
        self.create_subscription(Bool, '/fire_detected', self.fire_callback, 10)

        self.get_logger().info('Command node iniciado: monitoreando comandos y fuego')

    def command_callback(self, msg):
        self.get_logger().info(f'Comando web recibido en ROS: {msg.data}')

    def fire_callback(self, msg):
        self.get_logger().info(f'Estado fuego recibido en ROS: {msg.data}')


def main(args=None):
    rclpy.init(args=args)
    node = CommandNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

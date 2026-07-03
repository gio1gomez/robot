from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='robot_bombero',
            executable='uart_node',
            name='uart_node',
            output='screen',
            parameters=[
                {'serial_port': '/dev/serial0'},
                {'serial_baud': 115200},
            ],
        ),
        Node(
            package='robot_bombero',
            executable='detector_node',
            name='detector_node',
            output='screen',
            parameters=[
                {'model_path': '/root/prorob/best_float32.tflite'},
                {'camera_index': 0},
                {'confidence_threshold': 0.50},
                {'model_img_size': 320},
                {'infer_every_n_frames': 2},
                {'fire_frames_to_activate': 1},
                {'no_fire_frames_to_clear': 10},
            ],
        ),
        Node(
            package='robot_bombero',
            executable='web_node',
            name='web_node',
            output='screen',
            parameters=[
                {'template_folder': '/root/prorob/templates'},
            ],
        ),
        Node(
            package='robot_bombero',
            executable='command_node',
            name='command_node',
            output='screen',
        ),
    ])

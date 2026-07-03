from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'robot_bombero'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='giovani',
    maintainer_email='giovani@todo.todo',
    description='Robot bombero ROS 2 con YOLO, Flask, UART y Arduino Mega',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'uart_node = robot_bombero.uart_node:main',
            'detector_node = robot_bombero.detector_node:main',
            'web_node = robot_bombero.web_node:main',
            'command_node = robot_bombero.command_node:main',
        ],
    },
)

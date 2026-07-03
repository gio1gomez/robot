# Robot Bombero ROS 2

Proyecto ROS 2 Jazzy para Raspberry Pi 5 + Arduino Mega.

## Nodos

- `uart_node`: recibe `/robot_command` y `/fire_detected`, envía comandos por UART al Arduino Mega.
- `detector_node`: usa cámara USB + YOLO/TFLite y publica `/fire_detected` y `/camera/fire/image_jpeg`.
- `web_node`: sirve la página web Flask y publica comandos en `/robot_command`.
- `command_node`: monitor de depuración para ver comandos y detección.

## Arduino Mega

El Arduino Mega no se modifica. Sigue recibiendo por UART:

- FWD
- BACK
- LEFT
- RIGHT
- STOP
- SERVO_SWEEP_ON
- SERVO_SWEEP_OFF
- PUMP_ON
- PUMP_OFF
- FIRE_DETECTED
- FIRE_CLEARED

## Archivos necesarios

Copia tu modelo en:

```bash
prorob/best_float32.tflite
```

La página web está en:

```bash
prorob/templates/index.html
```

## Construir Docker

```bash
docker build -t robot_bombero_ros .
```

## Entrar al Docker

```bash
docker run -it --rm --net=host \
  --device=/dev/serial0 \
  --device=/dev/ttyAMA0 \
  --device=/dev/video0 \
  -v $PWD/ros2_ws:/root/ros2_ws \
  -v $PWD/prorob:/root/prorob \
  robot_bombero_ros
```

## Compilar ROS

Dentro del Docker:

```bash
source /opt/ros/jazzy/setup.bash
cd /root/ros2_ws
colcon build
source install/setup.bash
```

## Ejecutar todo con launch

```bash
ros2 launch robot_bombero robot.launch.py
```

## Abrir página web

En navegador:

```text
http://IP_DE_TU_RASPBERRY:5000
```

Ejemplo:

```text
http://10.126.44.8:5000
```

## Probar tópicos

```bash
ros2 topic list
ros2 topic echo /robot_command
ros2 topic echo /fire_detected
ros2 topic echo /camera/fire/image_jpeg
```

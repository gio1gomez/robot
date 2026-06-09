# Robot Diferencial Físico con Control PID en micro-ROS y ROS 2

## 1. Descripción del proyecto

Este proyecto implementa un robot diferencial físico controlado mediante una ESP32, micro-ROS y ROS 2 Jazzy. El robot recibe comandos de velocidad desde el tópico `/cmd_vel`, utilizando mensajes del tipo `geometry_msgs/msg/Twist`.

La ESP32 ejecuta un controlador PID independiente para cada motor. La retroalimentación se obtiene mediante los encoders de los motores, y la señal de actuación se envía al driver TB6612FNG mediante PWM.

## 2. Componentes utilizados

* ESP32 DevKit
* Driver TB6612FNG
* 2 motores DC con encoders
* Batería para alimentación de motores
* Protoboard y cables
* ROS 2 Jazzy
* micro-ROS Arduino
* micro-ROS Agent ejecutado en Docker

## 3. Estructura del repositorio

```text
robot_diferencial_pid/
├── README.md
├── docs/
│   └── evidencias/
├── firmware/
│   └── esp32_diff_pid_microros/
│       └── esp32_diff_pid_microros.ino
└── ros2/
    └── comandos_ros2.md
```

## 4. Conexiones principales

### 4.1 TB6612FNG a ESP32

| TB6612FNG | ESP32              |
| --------- | ------------------ |
| PWMA      | GPIO25             |
| AIN1      | GPIO26             |
| AIN2      | GPIO27             |
| PWMB      | GPIO14             |
| BIN1      | GPIO16             |
| BIN2      | GPIO17             |
| STBY      | GPIO23             |
| VCC       | 3.3V               |
| GND       | GND común          |
| VM        | Batería de motores |

Es importante que el GND de la ESP32, el GND del TB6612FNG y el GND de la batería estén unidos.

### 4.2 Motor izquierdo con encoder

| Pin del motor | Conexión          |
| ------------- | ----------------- |
| M1            | AO1 del TB6612FNG |
| M2            | AO2 del TB6612FNG |
| C1            | GPIO32 ESP32      |
| C2            | GPIO33 ESP32      |
| VCC           | 3.3V ESP32        |
| GND           | GND común         |

### 4.3 Motor derecho con encoder

| Pin del motor | Conexión          |
| ------------- | ----------------- |
| M1            | BO1 del TB6612FNG |
| M2            | BO2 del TB6612FNG |
| C1            | GPIO18 ESP32      |
| C2            | GPIO19 ESP32      |
| VCC           | 3.3V ESP32        |
| GND           | GND común         |

## 5. Parámetros PID

Los parámetros PID utilizados fueron ajustados experimentalmente a partir de pruebas con los motores y encoders.

```text
Kp = 0.035
Ki = 0.006
Kd = 0.0
```

El controlador PID compara la velocidad deseada con la velocidad medida por los encoders y ajusta el PWM de cada motor para reducir el error.

## 6. Funcionamiento general

El sistema funciona de la siguiente manera:

1. ROS 2 publica comandos de velocidad en el tópico `/cmd_vel`.
2. El micro-ROS Agent recibe los mensajes desde ROS 2.
3. La ESP32 recibe los comandos mediante micro-ROS por USB serial.
4. La ESP32 convierte `linear.x` y `angular.z` en velocidades objetivo para la rueda izquierda y derecha.
5. Los encoders miden la velocidad real de cada motor.
6. El controlador PID ajusta el PWM enviado al TB6612FNG.
7. El robot responde físicamente avanzando, retrocediendo o girando.

## 7. Ejecución del micro-ROS Agent

En una terminal ejecutar:

```bash
sudo docker run -it --rm --net=host --device=/dev/ttyUSB0 microros/micro-ros-agent:jazzy serial --dev /dev/ttyUSB0 -b 115200 -v6
```

Después de ejecutar el Agent, presionar el botón `EN/RESET` de la ESP32.

## 8. Verificación del nodo en ROS 2

En otra terminal ejecutar:

```bash
source /opt/ros/jazzy/setup.bash
ros2 node list
```

Debe aparecer el nodo:

```text
/esp32_diff_pid_robot
```

## 9. Comandos de prueba

### Avanzar

```bash
ros2 topic pub -r 5 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.20, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

### Retroceder

```bash
ros2 topic pub -r 5 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: -0.20, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

### Girar

```bash
ros2 topic pub -r 5 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}"
```

### Girar en sentido contrario

```bash
ros2 topic pub -r 5 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: -0.5}}"
```

### Detener

Primero detener el publicador con:

```text
Ctrl + C
```

Luego enviar velocidad cero:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

## 10. Evidencias

En la carpeta `docs/evidencias/` se incluyen capturas y fotografías del funcionamiento:

* Montaje físico del robot.
* micro-ROS Agent ejecutándose.
* Nodo `/esp32_diff_pid_robot` visible en ROS 2.
* Publicación de comandos en `/cmd_vel`.
* Respuesta física del robot.

## 11. Conclusión

Se logró implementar un robot diferencial físico con dos motores independientes y encoders para retroalimentación. La ESP32 ejecuta el controlador PID y recibe comandos desde ROS 2 mediante micro-ROS. El robot responde a comandos publicados en `/cmd_vel`, cumpliendo con el objetivo de integrar control PID, micro-ROS y ROS 2 en una plataforma física real.

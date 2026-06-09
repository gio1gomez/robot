# Comandos ROS 2 - Robot Diferencial PID con micro-ROS

## 1. Activar ROS 2 Jazzy

En cada terminal nueva donde se usen comandos ROS 2:

source /opt/ros/jazzy/setup.bash

---

## 2. Ejecutar micro-ROS Agent por USB serial

Este comando se ejecuta en la terminal 1.
Debe quedar corriendo mientras se usa el robot.


sudo docker run -it --rm --net=host --device=/dev/ttyUSB0 microros/micro-ros-agent:jazzy serial --dev /dev/ttyUSB0 -b 115200 -v6


Después de ejecutar el Agent, presionar el botón **EN/RESET** de la ESP32.

---

## 3. Verificar que la ESP32 aparece como nodo ROS 2

En otra terminal:


source /opt/ros/jazzy/setup.bash
ros2 node list


Debe aparecer:

```text
/esp32_diff_pid_robot
```

---

## 4. Verificar tópicos disponibles

```bash
ros2 topic list
```

Debe aparecer el tópico:

```text
/cmd_vel
```

---

## 5. Avanzar hacia adelante

```bash
ros2 topic pub -r 5 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.20, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

Más rápido:

```bash
ros2 topic pub -r 5 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.30, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

---

## 6. Retroceder

```bash
ros2 topic pub -r 5 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: -0.20, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

---

## 7. Girar en un sentido

```bash
ros2 topic pub -r 5 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}"
```

---

## 8. Girar en el sentido contrario

```bash
ros2 topic pub -r 5 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: -0.5}}"
```

---

## 9. Avanzar haciendo curva

```bash
ros2 topic pub -r 5 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.20, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.4}}"
```

Curva al otro lado:

```bash
ros2 topic pub -r 5 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.20, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: -0.4}}"
```

---

## 10. Detener el robot

Primero detener el publicador continuo con:

```text
Ctrl + C
```

Luego enviar comando de parada:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

---

## 11. Ver información del tópico `/cmd_vel`

```bash
ros2 topic info /cmd_vel
```

---

## 12. Ver el tipo de mensaje de `/cmd_vel`

```bash
ros2 interface show geometry_msgs/msg/Twist
```

---

## 13. Orden recomendado para ejecutar el sistema

1. Conectar la ESP32 por USB.
2. Conectar la alimentación de motores al pin VM del TB6612FNG.
3. Ejecutar el micro-ROS Agent.
4. Presionar EN/RESET en la ESP32.
5. Verificar el nodo con `ros2 node list`.
6. Enviar comandos al tópico `/cmd_vel`.
7. Detener el robot con comando de velocidad cero.

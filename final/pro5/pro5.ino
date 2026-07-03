#include <Servo.h>

#define UART_BAUD 115200

// L298N
#define ENA 5
#define ENB 6
#define IN1 2
#define IN2 3
#define IN3 4
#define IN4 8

// Servo
#define SERVO_PIN 7

// Relay bomba
#define RELAY_PIN 12

// Ultrasonico HC-SR04
#define TRIG_PIN 9
#define ECHO_PIN 10

int velocidad = 255;

// PID distancia
bool pidActive = false;
float targetDistance = 15.0; // cm

float Kp = 8.0;
float Ki = 0.0;
float Kd = 3.0;

float error = 0;
float lastError = 0;
float integral = 0;

unsigned long lastPidTime = 0;
const unsigned long PID_INTERVAL_MS = 100;

const float MIN_VALID_DISTANCE = 3.0;
const float MAX_VALID_DISTANCE = 120.0;
const int MIN_PWM = 80;
const int MAX_PWM = 190;
const float DEAD_ZONE_CM = 2.0;

Servo waterServo;

bool servoActive = false;
unsigned long lastServoMove = 0;

int servoAngle = 0;
int servoDirection = 1;

const unsigned long SERVO_INTERVAL_MS = 25;

void pumpOn() {
  digitalWrite(RELAY_PIN, HIGH);
  Serial.println("BOMBA ENCENDIDA");
}

void pumpOff() {
  digitalWrite(RELAY_PIN, LOW);
  Serial.println("BOMBA APAGADA");
}

void stopMotors() {
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);

  Serial.println("STOP");
}

void motorsForward(int pwm) {
  pwm = constrain(pwm, 0, 255);

  // Motor A adelante
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  // Motor B adelante invertido
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);

  analogWrite(ENA, pwm);
  analogWrite(ENB, pwm);
}

void motorsBackward(int pwm) {
  pwm = constrain(pwm, 0, 255);

  // Motor A atras
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);

  // Motor B atras invertido
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);

  analogWrite(ENA, pwm);
  analogWrite(ENB, pwm);
}

void forward() {
  pidActive = false;
  motorsForward(velocidad);
  Serial.println("ADELANTE");
}

void backward() {
  pidActive = false;
  motorsBackward(velocidad);
  Serial.println("ATRAS");
}

void left() {
  pidActive = false;

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);

  analogWrite(ENA, velocidad);
  analogWrite(ENB, velocidad);

  Serial.println("IZQUIERDA");
}

void right() {
  pidActive = false;

  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);

  analogWrite(ENA, velocidad);
  analogWrite(ENB, velocidad);

  Serial.println("DERECHA");
}

float readDistanceOnceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000);

  if (duration == 0) {
    return -1;
  }

  return duration * 0.0343 / 2.0;
}

float readDistanceCm() {
  float sum = 0;
  int validCount = 0;

  for (int i = 0; i < 5; i++) {
    float d = readDistanceOnceCm();

    if (d >= MIN_VALID_DISTANCE && d <= MAX_VALID_DISTANCE) {
      sum += d;
      validCount++;
    }

    delay(5);
  }

  if (validCount == 0) {
    return -1;
  }

  return sum / validCount;
}

void startServo() {
  if (!servoActive) {
    servoAngle = 0;
    servoDirection = 1;
    waterServo.write(servoAngle);
  }

  servoActive = true;
  lastServoMove = millis();

  Serial.println("SERVO ENCENDIDO");
}

void stopServo() {
  servoActive = false;
  waterServo.write(90);

  Serial.println("SERVO APAGADO");
}

void updateServo() {
  if (!servoActive) return;

  unsigned long now = millis();

  if (now - lastServoMove >= SERVO_INTERVAL_MS) {
    lastServoMove = now;

    waterServo.write(servoAngle);

    servoAngle += servoDirection * 5;

    if (servoAngle >= 180) {
      servoAngle = 180;
      servoDirection = -1;
    }

    if (servoAngle <= 0) {
      servoAngle = 0;
      servoDirection = 1;
    }
  }
}

void startPID() {
  pidActive = true;
  integral = 0;
  lastError = 0;
  lastPidTime = millis();

  Serial.println("PID DISTANCIA ACTIVADO");
}

void stopPID() {
  pidActive = false;
  stopMotors();

  Serial.println("PID DISTANCIA APAGADO");
}

void updatePID() {
  if (!pidActive) return;

  unsigned long now = millis();

  if (now - lastPidTime < PID_INTERVAL_MS) {
    return;
  }

  float dt = (now - lastPidTime) / 1000.0;
  lastPidTime = now;

  float distance = readDistanceCm();

  if (distance < 0) {
    stopMotors();
    Serial.println("PID: sin lectura valida");
    return;
  }

  error = distance - targetDistance;

  if (abs(error) <= DEAD_ZONE_CM) {
    integral = 0;
    stopMotors();
    Serial.print("PID OK | Distancia: ");
    Serial.println(distance);
    return;
  }

  integral += error * dt;
  integral = constrain(integral, -30, 30);

  float derivative = (error - lastError) / dt;
  lastError = error;

  float output = Kp * error + Ki * integral + Kd * derivative;
  int pwm = constrain(abs(output), MIN_PWM, MAX_PWM);

  if (error > 0) {
    motorsForward(pwm);
    Serial.print("PID AVANZA | Distancia: ");
    Serial.print(distance);
    Serial.print(" cm | PWM: ");
    Serial.println(pwm);
  } else {
    motorsBackward(pwm);
    Serial.print("PID RETROCEDE | Distancia: ");
    Serial.print(distance);
    Serial.print(" cm | PWM: ");
    Serial.println(pwm);
  }
}

void fireDetected() {
  startServo();
  pumpOn();
  startPID();

  Serial.println("FUEGO DETECTADO: SERVO + BOMBA + PID ACTIVADOS");
}

void fireCleared() {
  stopServo();
  pumpOff();
  stopPID();

  Serial.println("FUEGO LIMPIADO: SERVO + BOMBA + PID APAGADOS");
}

void handleCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();

  Serial.print("Comando recibido: ");
  Serial.println(cmd);

  if (cmd == "FWD") {
    forward();
  }
  else if (cmd == "BACK") {
    backward();
  }
  else if (cmd == "LEFT") {
    left();
  }
  else if (cmd == "RIGHT") {
    right();
  }
  else if (cmd == "STOP") {
    pidActive = false;
    stopMotors();
  }
  else if (cmd == "FIRE_DETECTED") {
    fireDetected();
  }
  else if (cmd == "FIRE_CLEARED") {
    fireCleared();
  }
  else if (cmd == "SERVO_SWEEP_ON") {
    startServo();
  }
  else if (cmd == "SERVO_SWEEP_OFF") {
    stopServo();
  }
  else if (cmd == "PUMP_ON") {
    pumpOn();
  }
  else if (cmd == "PUMP_OFF") {
    pumpOff();
  }
  else {
    Serial.println("Comando no reconocido");
  }
}

void setup() {
  Serial.begin(9600);
  Serial1.begin(UART_BAUD);

  Serial.setTimeout(50);
  Serial1.setTimeout(50);

  pinMode(ENA, OUTPUT);
  pinMode(ENB, OUTPUT);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  waterServo.attach(SERVO_PIN);
  waterServo.write(90);

  stopMotors();
  pumpOff();

  Serial.println("Arduino Mega listo");
  Serial.println("Distancia objetivo PID: 15 cm");
}

void loop() {
  if (Serial1.available()) {
    String cmd = Serial1.readStringUntil('\n');
    handleCommand(cmd);
  }

  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    handleCommand(cmd);
  }

  updateServo();
  updatePID();
}

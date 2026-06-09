#include <micro_ros_arduino.h>

#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

#include <geometry_msgs/msg/twist.h>

// ==========================
// Pines TB6612FNG
// ==========================

// Motor A - Izquierdo
const int PWMA = 25;
const int AIN1 = 26;
const int AIN2 = 27;

// Motor B - Derecho
const int PWMB = 14;
const int BIN1 = 16;
const int BIN2 = 17;

// Standby
const int STBY = 23;

// LED interno ESP32
const int LED_PIN = 2;

// ==========================
// Encoders
// ==========================

const int ENC_L_A = 32;  // C1 izquierdo
const int ENC_L_B = 33;  // C2 izquierdo

const int ENC_R_A = 18;  // C1 derecho
const int ENC_R_B = 19;  // C2 derecho

volatile long ticksLeft = 0;
volatile long ticksRight = 0;

long lastTicksLeft = 0;
long lastTicksRight = 0;

// ==========================
// PWM
// ==========================

const int PWM_FREQ = 1000;
const int PWM_RESOLUTION = 8;

// ==========================
// PID calibrado
// ==========================

float Kp = 0.035;
float Ki = 0.006;
float Kd = 0.0;

float integralL = 0;
float integralR = 0;

float lastErrorL = 0;
float lastErrorR = 0;

float pwmL = 35;
float pwmR = 35;

int maxPWM = 90;

// ==========================
// Conversión cmd_vel a ticks/s
// Ajustable luego
// ==========================

// Con esto: linear.x = 0.15 aprox equivale a 120 ticks/s
float LINEAR_TO_TICKS = 800.0;

// Con esto: angular.z genera diferencia entre ruedas
float ANGULAR_TO_TICKS = 100.0;

float targetLeft = 0.0;
float targetRight = 0.0;

unsigned long lastControlTime = 0;
unsigned long lastCmdTime = 0;

// Si no recibe /cmd_vel en 1 segundo, se detiene
const unsigned long CMD_TIMEOUT_MS = 1000;

// ==========================
// micro-ROS
// ==========================

rcl_subscription_t subscriber;
geometry_msgs__msg__Twist cmd_msg;

rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

#define RCCHECK(fn) { \
  rcl_ret_t temp_rc = fn; \
  if ((temp_rc != RCL_RET_OK)) { error_loop(); } \
}

#define RCSOFTCHECK(fn) { \
  rcl_ret_t temp_rc = fn; \
  if ((temp_rc != RCL_RET_OK)) {} \
}

// ==========================
// Interrupciones encoders
// ==========================

void IRAM_ATTR encoderLeftISR() {
  int b = digitalRead(ENC_L_B);

  if (b == HIGH) {
    ticksLeft++;
  } else {
    ticksLeft--;
  }
}

void IRAM_ATTR encoderRightISR() {
  int b = digitalRead(ENC_R_B);

  if (b == HIGH) {
    ticksRight++;
  } else {
    ticksRight--;
  }
}

// ==========================
// Callback /cmd_vel
// ==========================

void cmdVelCallback(const void *msgin) {
  const geometry_msgs__msg__Twist *msg =
    (const geometry_msgs__msg__Twist *)msgin;

  float linear = msg->linear.x;
  float angular = msg->angular.z;

  // Robot diferencial:
  // izquierda = avance - giro
  // derecha   = avance + giro
  targetLeft = (linear * LINEAR_TO_TICKS) - (angular * ANGULAR_TO_TICKS);
  targetRight = (linear * LINEAR_TO_TICKS) + (angular * ANGULAR_TO_TICKS);

  // Límite de seguridad en ticks/s
  targetLeft = constrain(targetLeft, -180.0, 180.0);
  targetRight = constrain(targetRight, -180.0, 180.0);

  lastCmdTime = millis();

  // Parpadea cuando recibe comando
  digitalWrite(LED_PIN, !digitalRead(LED_PIN));
}

// ==========================
// Error micro-ROS
// ==========================

void error_loop() {
  pararMotores();

  while (1) {
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    delay(200);
  }
}

// ==========================
// Setup
// ==========================

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // Pines motores
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pinMode(BIN1, OUTPUT);
  pinMode(BIN2, OUTPUT);
  pinMode(STBY, OUTPUT);

  digitalWrite(STBY, HIGH);

  // PWM ESP32
  ledcAttach(PWMA, PWM_FREQ, PWM_RESOLUTION);
  ledcAttach(PWMB, PWM_FREQ, PWM_RESOLUTION);

  pararMotores();

  // Encoders
  pinMode(ENC_L_A, INPUT_PULLUP);
  pinMode(ENC_L_B, INPUT_PULLUP);
  pinMode(ENC_R_A, INPUT_PULLUP);
  pinMode(ENC_R_B, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(ENC_L_A), encoderLeftISR, RISING);
  attachInterrupt(digitalPinToInterrupt(ENC_R_A), encoderRightISR, RISING);

  // Transporte micro-ROS por cable USB
  set_microros_transports();

  delay(2000);

  allocator = rcl_get_default_allocator();

  RCCHECK(rclc_support_init(&support, 0, NULL, &allocator));

  RCCHECK(rclc_node_init_default(
    &node,
    "esp32_diff_pid_robot",
    "",
    &support
  ));

  RCCHECK(rclc_subscription_init_default(
    &subscriber,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist),
    "cmd_vel"
  ));

  RCCHECK(rclc_executor_init(
    &executor,
    &support.context,
    1,
    &allocator
  ));

  RCCHECK(rclc_executor_add_subscription(
    &executor,
    &subscriber,
    &cmd_msg,
    &cmdVelCallback,
    ON_NEW_DATA
  ));

  lastControlTime = millis();
  lastCmdTime = millis();
}

// ==========================
// Loop
// ==========================

void loop() {
  RCSOFTCHECK(rclc_executor_spin_some(
    &executor,
    RCL_MS_TO_NS(20)
  ));

  unsigned long now = millis();

  // Seguridad: si no llega comando, detener
  if (now - lastCmdTime > CMD_TIMEOUT_MS) {
    targetLeft = 0.0;
    targetRight = 0.0;
  }

  // Control PID cada 500 ms, igual que la prueba estable
  if (now - lastControlTime >= 500) {
    controlPID();
    lastControlTime = now;
  }

  delay(5);
}

// ==========================
// Control PID
// ==========================

void controlPID() {
  long currentLeft;
  long currentRight;

  noInterrupts();
  currentLeft = ticksLeft;
  currentRight = ticksRight;
  interrupts();

  long deltaLeft = currentLeft - lastTicksLeft;
  long deltaRight = currentRight - lastTicksRight;

  lastTicksLeft = currentLeft;
  lastTicksRight = currentRight;

  float dt = 0.5; // 500 ms

  float speedLeft = abs(deltaLeft / dt);
  float speedRight = abs(deltaRight / dt);

  float desiredLeft = abs(targetLeft);
  float desiredRight = abs(targetRight);

  // Si target es casi cero, detener motor
  if (desiredLeft < 5.0) {
    pwmL = 0;
    integralL = 0;
    lastErrorL = 0;
  } else {
    float errorL = desiredLeft - speedLeft;

    integralL += errorL * dt;
    integralL = constrain(integralL, -300, 300);

    float derivativeL = (errorL - lastErrorL) / dt;

    float correctionL = Kp * errorL + Ki * integralL + Kd * derivativeL;

    pwmL += correctionL;
    pwmL = constrain(pwmL, 0, maxPWM);

    lastErrorL = errorL;
  }

  if (desiredRight < 5.0) {
    pwmR = 0;
    integralR = 0;
    lastErrorR = 0;
  } else {
    float errorR = desiredRight - speedRight;

    integralR += errorR * dt;
    integralR = constrain(integralR, -300, 300);

    float derivativeR = (errorR - lastErrorR) / dt;

    float correctionR = Kp * errorR + Ki * integralR + Kd * derivativeR;

    pwmR += correctionR;
    pwmR = constrain(pwmR, 0, maxPWM);

    lastErrorR = errorR;
  }

  int commandLeft = 0;
  int commandRight = 0;

  if (targetLeft > 5.0) {
    commandLeft = (int)pwmL;
  } else if (targetLeft < -5.0) {
    commandLeft = -(int)pwmL;
  }

  if (targetRight > 5.0) {
    commandRight = (int)pwmR;
  } else if (targetRight < -5.0) {
    commandRight = -(int)pwmR;
  }

  motorIzquierdo(commandLeft);
  motorDerecho(commandRight);
}

// ==========================
// Motores
// ==========================

void motorIzquierdo(int pwm) {
  pwm = constrain(pwm, -255, 255);

  if (pwm > 0) {
    digitalWrite(AIN1, HIGH);
    digitalWrite(AIN2, LOW);
    ledcWrite(PWMA, pwm);
  } else if (pwm < 0) {
    digitalWrite(AIN1, LOW);
    digitalWrite(AIN2, HIGH);
    ledcWrite(PWMA, -pwm);
  } else {
    digitalWrite(AIN1, LOW);
    digitalWrite(AIN2, LOW);
    ledcWrite(PWMA, 0);
  }
}

void motorDerecho(int pwm) {
  pwm = constrain(pwm, -255, 255);

  if (pwm > 0) {
    digitalWrite(BIN1, HIGH);
    digitalWrite(BIN2, LOW);
    ledcWrite(PWMB, pwm);
  } else if (pwm < 0) {
    digitalWrite(BIN1, LOW);
    digitalWrite(BIN2, HIGH);
    ledcWrite(PWMB, -pwm);
  } else {
    digitalWrite(BIN1, LOW);
    digitalWrite(BIN2, LOW);
    ledcWrite(PWMB, 0);
  }
}

void pararMotores() {
  ledcWrite(PWMA, 0);
  ledcWrite(PWMB, 0);

  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, LOW);
  digitalWrite(BIN1, LOW);
  digitalWrite(BIN2, LOW);
}
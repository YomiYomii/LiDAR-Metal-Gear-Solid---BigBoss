//pines motor
#define IN1 25
#define IN2 19
#define IN3 18
#define IN4 13
//pines I2C (evitan los pines del motor; deben coincidir con el cableado real del VL53L0X)
#define SDA_PIN 21
#define SCL_PIN 22
//librerias para VL53L0X
#include <Wire.h>
#include <VL53L0X.h>

VL53L0X sensor;

const int PASOS_POR_VUELTA = 4096; //medios-pasos del motor por vuelta del EJE DEL MOTOR
const float REDUCCION = 2.0f; //reduccion fisica 2:1 (el motor gira 2 veces por cada vuelta del cabezal del sensor)
const float ANGULO_BARRIDO = 360; //angulo de barrido FISICO objetivo (el que recorre el cabezal del sensor)
//el motor debe girar ANGULO_BARRIDO*REDUCCION grados para que el cabezal barra ANGULO_BARRIDO grados
const int PASOS_BARRIDO = (int)(PASOS_POR_VUELTA * (ANGULO_BARRIDO * REDUCCION / 360.0f));

//tomamos una medida cada N pasos en vez de en cada paso: el motor avanza rapido
//y aun asi se recogen muchos puntos. Subelo para ir mas rapido, bajalo para mas resolucion.
const int PASOS_POR_MEDICION = 16;

//secuencia que permite los pasos del motor
const int secuencia[8][4] = {
  {1, 0, 0, 0},
  {1, 1, 0, 0},
  {0, 1, 0, 0},
  {0, 1, 1, 0},
  {0, 0, 1, 0},
  {0, 0, 1, 1},
  {0, 0, 0, 1},
  {1, 0, 0, 1}
};

int pasoActual = 0;

//funcion para dar un paso
void aplicarPaso(int paso) {
  digitalWrite(IN1, secuencia[paso][0]);
  digitalWrite(IN2, secuencia[paso][1]);
  digitalWrite(IN3, secuencia[paso][2]);
  digitalWrite(IN4, secuencia[paso][3]);
}

//funcion medir distancia con el sensor VL53L0X, notar la suma en "rho" que es la distancia desde el sensor al eje del motor
void medir(int paso, bool horario) {
  float anguloMotor = (paso * 360.0f) / PASOS_POR_VUELTA; //grados que ha girado el motor
  float theta = anguloMotor / REDUCCION;                  //grados reales del cabezal del sensor
  if (!horario) theta = ANGULO_BARRIDO - theta;

  uint16_t rho = sensor.readRangeContinuousMillimeters() + 77;
  if (sensor.timeoutOccurred()) {
    return;
  }

  Serial.printf("%.2f,%u\n", theta, rho);
}

//funcion mover el motor en el angulo de barrido ida y vuelta, notar que "pasos" debe estar en base 8
void mover(int pasos, bool horario) {
  for (int i = 0; i < pasos; i++) {
    if (horario) {
      pasoActual = (pasoActual + 1) % 8;
    } else {
      pasoActual = (pasoActual - 1 + 8 ) % 8;
    }
    aplicarPaso(pasoActual);
    if (i % PASOS_POR_MEDICION == 0) {
      medir(i, horario);
    }
    delayMicroseconds(1500); //tiempo entre pasos del 28BYJ-48 (no bajar mucho o el motor pierde pasos)
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  Wire.begin(SDA_PIN, SCL_PIN);
  if (!sensor.init()) {
    Serial.println("Error: sensor VL53L0X no encontrado");
    while (1);
  }
  sensor.setTimeout(500);
  sensor.setMeasurementTimingBudget(20000); //20 ms por medida (mas rapido; el default es ~33 ms)
  sensor.startContinuous();                  //modo continuo: mide sin parar, la lectura casi no bloquea

  Serial.println("theta_deg,rho_mm");
}
void loop() {
  delay(30000);
  mover(PASOS_BARRIDO, true);
  delay(100); 
  mover(PASOS_BARRIDO, false);
  delay(10000); 
}


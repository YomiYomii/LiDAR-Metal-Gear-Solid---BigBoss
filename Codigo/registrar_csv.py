import csv
import sys
import time
from collections import defaultdict

import serial

DEFAULT_PORT = "COM3"
DEFAULT_BAUD = 115200
DEFAULT_OUT = "mediciones.csv"

DECIMALES_ANGULO = 2


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PORT
    baud = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_BAUD
    out_path = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_OUT

    print(f"Conectando a {port} @ {baud} baudios...")
    ser = serial.Serial(port, baud, timeout=1)
    time.sleep(2)  #esperar a que el ESP32 reinicie tras abrir el puerto

    suma_rho = defaultdict(float)
    n_lecturas = defaultdict(int)

    try:
        while True:
            linea = ser.readline().decode("utf-8", errors="ignore").strip()
            if not linea:
                continue

            partes = linea.split(",")
            if len(partes) != 2:
                continue

            try:
                theta = float(partes[0])
                rho = float(partes[1])
            except ValueError:
                continue

            theta = round(theta % 360.0, DECIMALES_ANGULO)

            suma_rho[theta] += rho
            n_lecturas[theta] += 1
            print(linea)
    except KeyboardInterrupt:
        print("\nDetenido por el usuario. Calculando promedios...")
    finally:
        ser.close()

    if not n_lecturas:
        print("No se registraron mediciones; no se escribio ningun archivo.")
        return

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["theta_deg", "rho_mm", "n_pasadas"])
        for theta in sorted(suma_rho):
            promedio = suma_rho[theta] / n_lecturas[theta]
            writer.writerow([f"{theta:.2f}", f"{promedio:.1f}", n_lecturas[theta]])

    print(f"Listo: {len(suma_rho)} angulos guardados en {out_path}.")


if __name__ == "__main__":
    main()

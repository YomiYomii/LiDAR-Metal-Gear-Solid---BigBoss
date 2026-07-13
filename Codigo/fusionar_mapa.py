"""
Fusiona multiples escaneos del LiDAR (tomados desde distintas posiciones fisicas
del rig) en un unico mapa del entorno, mediante "odometria simulada" basada en
puntos de referencia fijos (landmarks).

Tecnica: dado que no hay odometria fisica (encoders de ruedas), la pose relativa
entre dos escaneos se estima con el algoritmo de Kabsch/Procrustes (Kabsch 1976;
Horn 1987, "Closed-form solution of absolute orientation using unit quaternions";
Umeyama 1991) a partir de >=2 landmarks fijos observados en ambos escaneos. Las
poses se encadenan igual que se integraria una odometria real, y cada escaneo se
transforma al marco de referencia global (definido por el primer escaneo).

Requisitos:
    pip install numpy matplotlib

Uso:
    1. Toma un escaneo por cada posicion del rig con registrar_csv.py
       (ej. escaneo_0.csv, escaneo_1.csv, ...).
    2. Con ver_escaneo.py identifica, para cada par de escaneos que se superponen,
       al menos 2 puntos fijos del entorno (esquinas, objetos, etc.) visibles en
       ambos, y anota su (theta_deg, rho_mm) tal como aparecen en cada escaneo.
    3. Completa ARCHIVOS_ESCANEOS y LANDMARKS abajo con esos datos.
    4. Ejecuta: python fusionar_mapa.py
"""

import csv

import matplotlib.pyplot as plt
import numpy as np

# --- Escaneos a fusionar, en el orden en que se tomaron ---
ARCHIVOS_ESCANEOS = [
    "mediciones_5.csv",
    "mediciones_4.csv"
]

# --- Puntos de referencia fijos (landmarks) ---
# Cada landmark es un mismo punto fisico del entorno, observado desde varios
# escaneos. Se listan como (indice_escaneo, theta_deg, rho_mm) tal como fue
# leido en el .csv de ese escaneo. Cada par de escaneos consecutivos necesita
# al menos 2 landmarks en comun (3+ para promediar error de medicion).
LANDMARKS = {
    "L1": [(0, 317.81, 366.5), (1, 336.8, 649.5)],
    "L2": [(0, 55.55, 454.5), (1, 37.27, 724)]
}


def cargar_escaneo(path):
    puntos = []
    with open(path, newline="") as f:
        for fila in csv.reader(f):
            if len(fila) < 2:
                continue
            try:
                # usa solo las 2 primeras columnas (theta, rho); ignora extras como n_pasadas
                puntos.append((float(fila[0]), float(fila[1])))
            except ValueError:
                continue  # encabezado u otra linea no numerica
    return puntos


def polar_a_cartesiano(theta_deg, rho_mm):
    theta_rad = np.radians(theta_deg)
    return rho_mm * np.cos(theta_rad), rho_mm * np.sin(theta_rad)


def kabsch_2d(P, Q):
    """Estima R, t tales que R @ P_i + t ~= Q_i (minimos cuadrados)."""
    P = np.asarray(P, dtype=float)
    Q = np.asarray(Q, dtype=float)
    p_mean = P.mean(axis=0)
    q_mean = Q.mean(axis=0)
    Pc = P - p_mean
    Qc = Q - q_mean

    H = Pc.T @ Qc
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1.0, d]) @ U.T
    t = q_mean - R @ p_mean

    residuales = (R @ P.T).T + t - Q
    rms = np.sqrt(np.mean(np.sum(residuales**2, axis=1)))
    return R, t, rms


def landmarks_en_local(landmarks, idx_escaneo):
    """{id_landmark: (x, y)} en coordenadas locales del escaneo idx_escaneo."""
    puntos = {}
    for lid, observaciones in landmarks.items():
        for idx, theta, rho in observaciones:
            if idx == idx_escaneo:
                puntos[lid] = polar_a_cartesiano(theta, rho)
    return puntos


def fusionar(archivos, landmarks):
    escaneos_locales = [cargar_escaneo(a) for a in archivos]
    n = len(archivos)

    # El primer escaneo define el marco de referencia global (pose identidad).
    poses = [(np.eye(2), np.zeros(2))]
    landmarks_globales = landmarks_en_local(landmarks, 0)

    for i in range(1, n):
        locales_i = landmarks_en_local(landmarks, i)
        comunes = sorted(set(locales_i) & set(landmarks_globales))
        if len(comunes) < 2:
            raise ValueError(
                f"Escaneo {i} ({archivos[i]}): se necesitan >=2 landmarks en "
                f"comun con el marco global ya resuelto (hay {len(comunes)})."
            )

        P = np.array([locales_i[c] for c in comunes])
        Q = np.array([landmarks_globales[c] for c in comunes])

        R, t, rms = kabsch_2d(P, Q)
        poses.append((R, t))

        angulo = np.degrees(np.arctan2(R[1, 0], R[0, 0]))
        print(
            f"Escaneo {i} ({archivos[i]}): landmarks usados={comunes}, "
            f"traslacion=({t[0]:.1f}, {t[1]:.1f}) mm, rotacion={angulo:.2f} deg, "
            f"error RMS={rms:.2f} mm"
        )

        for lid, (x, y) in locales_i.items():
            if lid not in landmarks_globales:
                landmarks_globales[lid] = tuple(R @ np.array([x, y]) + t)

    mapa = []
    for i, puntos in enumerate(escaneos_locales):
        R, t = poses[i]
        for theta, rho in puntos:
            x, y = polar_a_cartesiano(theta, rho)
            mapa.append(R @ np.array([x, y]) + t)

    return np.array(mapa), poses, landmarks_globales


def graficar(mapa, poses, landmarks_globales):
    plt.figure(figsize=(8, 8))
    plt.scatter(mapa[:, 0], mapa[:, 1], s=3, c="steelblue", label="Puntos del entorno")

    trayectoria = np.array([t for _, t in poses])
    plt.plot(
        trayectoria[:, 0], trayectoria[:, 1], "o-", c="red",
        label="Pose del sensor (odometria simulada)",
    )

    for lid, (x, y) in landmarks_globales.items():
        plt.scatter(x, y, marker="x", s=90, c="black")
        plt.annotate(lid, (x, y))

    plt.axis("equal")
    plt.xlabel("x (mm)")
    plt.ylabel("y (mm)")
    plt.title("Mapa fusionado del entorno")
    plt.legend()
    plt.grid(True)
    plt.savefig("mapa_fusionado.png", dpi=150)
    plt.show()


if __name__ == "__main__":
    mapa, poses, landmarks_globales = fusionar(ARCHIVOS_ESCANEOS, LANDMARKS)
    graficar(mapa, poses, landmarks_globales)

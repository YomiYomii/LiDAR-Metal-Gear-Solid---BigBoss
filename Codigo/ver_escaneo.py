"""
Visualiza un unico escaneo (theta_deg, rho_mm) en coordenadas cartesianas,
para identificar visualmente los puntos de referencia fijos (landmarks) que
luego se usaran en fusionar_mapa.py.

Haz CLIC sobre cualquier punto del grafico y el programa te mostrara su theta y
rho exactos (en la ventana y tambien en la terminal), listos para copiar a
fusionar_mapa.py. No tienes que buscar nada a mano en el .csv.

Uso:
    python ver_escaneo.py escaneo_0.csv
"""

import csv
import sys

import matplotlib.pyplot as plt
import numpy as np


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


def main():
    if len(sys.argv) < 2:
        print("Uso: python ver_escaneo.py <archivo.csv>")
        return

    puntos = cargar_escaneo(sys.argv[1])
    thetas = np.array([p[0] for p in puntos])
    rhos = np.array([p[1] for p in puntos])
    x = rhos * np.cos(np.radians(thetas))
    y = rhos * np.sin(np.radians(thetas))

    fig, ax = plt.subplots(figsize=(7, 7))
    sc = ax.scatter(x, y, c=thetas, cmap="viridis", s=10)
    paso_anotacion = max(1, len(puntos) // 40)
    for i in range(0, len(puntos), paso_anotacion):
        ax.annotate(f"{thetas[i]:.0f}°", (x[i], y[i]), fontsize=7)

    plt.colorbar(sc, label="theta (deg)")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title(f"Escaneo: {sys.argv[1]}\nHaz clic en un punto para ver su theta y rho")
    ax.axis("equal")
    ax.grid(True)

    # marcador y etiqueta que se mueven al punto mas cercano cada vez que haces clic
    resaltado, = ax.plot([], [], "o", color="red", markersize=12, fillstyle="none", mew=2)
    etiqueta = ax.annotate(
        "", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
        bbox=dict(boxstyle="round", fc="yellow", alpha=0.9), fontsize=9,
    )
    etiqueta.set_visible(False)

    def al_hacer_clic(event):
        if event.inaxes != ax or event.xdata is None:
            return
        # punto medido mas cercano al clic
        i = int(np.argmin((x - event.xdata) ** 2 + (y - event.ydata) ** 2))
        texto = f"theta={thetas[i]:.2f}, rho={rhos[i]:.1f}"
        print(f"Punto seleccionado -> {texto}   (para fusionar_mapa.py: {thetas[i]:.2f}, {rhos[i]:.1f})")
        resaltado.set_data([x[i]], [y[i]])
        etiqueta.xy = (x[i], y[i])
        etiqueta.set_text(texto)
        etiqueta.set_visible(True)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("button_press_event", al_hacer_clic)
    plt.show()


if __name__ == "__main__":
    main()

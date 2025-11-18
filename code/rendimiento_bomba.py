import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ============================================================
# 1. Puntos tomados del gráfico del fabricante (Q en L/s)
# ============================================================

head_points = [
    (40, 970),
    (80, 960),
    (160, 890),
    (200, 840),
    (280, 620)
]

eff_points = [
    (40, 33),
    (80, 56),
    (160, 81),
    (220, 85),
    (280, 79)
]

power_points = [
    (40, 1200),
    (80, 1400),
    (160, 1750),
    (200, 1950),
    (260, 2150),
    (280, 3400)
]

npsh_points = [
    (80, 4.5),
    (160, 5.0),
    (200, 7.2),
    (240, 11.0),
    (280, 17.0)
]

# ============================================================
# 2. Interpoladores lineales para las curvas suaves
# ============================================================

def build_interp(points):
    points_sorted = sorted(points, key=lambda p: p[0])
    q = np.array([p[0] for p in points_sorted], dtype=float)
    y = np.array([p[1] for p in points_sorted], dtype=float)

    def interp_func(q_new):
        return np.interp(q_new, q, y)
    return interp_func, q.min(), q.max()

head_interp, qmin_h, qmax_h   = build_interp(head_points)
eff_interp, qmin_e, qmax_e    = build_interp(eff_points)
npsh_interp, qmin_n, qmax_n   = build_interp(npsh_points)

# Rango común de caudales
q_min = max(qmin_h, qmin_e, qmin_n)
q_max = min(qmax_h, qmax_e, qmax_n)

# ============================================================
# 3. Generar tabla interpolada (solo para Head, Eff, NPSHr)
# ============================================================

n_points = 100
Q = np.linspace(q_min, q_max, n_points)

H = head_interp(Q)
eta = eff_interp(Q)
NPSHr = npsh_interp(Q)

# ============================================================
# 4. Potencia: solo unión de puntos originales
# ============================================================

Q_power = [p[0] for p in power_points]
P = [p[1] for p in power_points]

# ============================================================
# 5. Calcular potencia hidráulica teórica y eficiencia real
# ============================================================

rho = 1000  # agua
g = 9.81
Q_m3s = Q / 1000
Ph_kW = rho * g * Q_m3s * H / 1000  # en kW

# Para comparar eficiencia hidráulica real vs. fabricante
# Se interpolan las potencias medidas a partir de los puntos reales
P_interp = np.interp(Q, Q_power, P)
rendimiento_real = 100 * (Ph_kW / P_interp)

# Crear DataFrame
df = pd.DataFrame({
    "Q_Ls": Q,
    "Head_m": H,
    "Eff_%_fabricante": eta,
    "Power_kW_interp": P_interp,
    "NPSHr_m": NPSHr,
    "Ph_kW_teorico": Ph_kW,
    "Eficiencia_real_%": rendimiento_real
})

df.to_csv("curva_bomba_interpolada.csv", index=False)
print("Archivo 'curva_bomba_interpolada.csv' generado.")

# ============================================================
# 6. Gráficos
# ============================================================

plt.figure(figsize=(8,6))
plt.plot(Q, H, label="Head (m)", lw=2)
plt.xlabel("Caudal (L/s)")
plt.ylabel("Altura (m)")
plt.title("Curva H-Q (Altura vs Caudal)")
plt.grid(True)
plt.legend()
plt.show()

plt.figure(figsize=(8,6))
plt.plot(Q, eta, 'g', lw=2, label="Eficiencia fabricante (%)")
plt.plot(Q, rendimiento_real, 'r--', label="Eficiencia calculada (%)")
plt.xlabel("Caudal (L/s)")
plt.ylabel("Eficiencia (%)")
plt.title("Curva de Eficiencia")
plt.grid(True)
plt.legend()
plt.show()

plt.figure(figsize=(8,6))
plt.plot(Q_power, P, 'bo-', lw=2, label="Potencia (puntos reales)")
plt.xlabel("Caudal (L/s)")
plt.ylabel("Potencia (kW)")
plt.title("Curva de Potencia (sin interpolar)")
plt.grid(True)
plt.legend()
plt.show()

plt.figure(figsize=(8,6))
plt.plot(Q, NPSHr, 'm', lw=2, label="NPSHr (m)")
plt.xlabel("Caudal (L/s)")
plt.ylabel("NPSHr (m)")
plt.title("Curva de NPSHr")
plt.grid(True)
plt.legend()
plt.show()

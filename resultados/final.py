#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sistema de Impulsión - Tranque Ovejería
---------------------------------------

- Cálculo hidráulico por tramos (API 5L X65, Swamee-Jain)
- Selección de estaciones según configuración de bombas
- Dimensionamiento de estanques de amortiguación
- Cálculo de espesor de tubería por ASME B31.4
- Gráficos principales:
  * Curva H-Q, eficiencia, potencia
  * Perfil longitudinal y línea de energía
  * Head por estación

Resultados:
  * Excel con resumen completo
  * PNGs con gráficos
"""

import os
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------------
# Parámetros globales
# -------------------------------
Q_total = 0.8  # m3/s (800 L/s)
rho = 1000.0   # kg/m3
g = 9.81       # m/s2
nu = 1e-6      # m2/s (agua 20°C)

t_res = 30 * 60  # 30 minutos de reserva
SAVE_PLOTS = True

# Curvas de bomba Goulds 3600
head_pts = [(40, 970), (80, 960), (160, 890), (200, 840), (280, 620)]
eff_pts = [(40, 33), (80, 56), (160, 81), (220, 85), (280, 79)]
power_pts = [(40, 1200), (80, 1400), (160, 1750), (200, 1950), (260, 2150), (280, 3400)]

# -------------------------------
# Tramos y alturas:
# -------------------------------
TRAMOS = [
    ("2-3", 23000.0, 845),
    ("3-4", 2870.0, 40),
    ("4-5", 7840.0, 617),
    ("5-6", 8670.0, 125),
    ("6-7", 320.0, -18),
    ("7-8", 9900.0, 170),
    ("8-9", 5870.0, 375),
]

ALT = {"2": 745, "3": 1590, "4": 1630, "5": 2247, "6": 2372, "7": 2354, "8": 2524, "9": 2899}

# -------------------------------
# Funciones auxiliares
# -------------------------------
def build_interp(pts):
    """Retorna una interpolación lineal con extrapolación suave."""
    x, y = zip(*sorted(pts))
    x, y = np.array(x), np.array(y)
    def f(q):
        return float(np.interp(q, x, y))
    return f, min(x), max(x)

def swamee_jain_f(Re, eps, D):
    """Factor Darcy Swamee-Jain"""
    if Re < 2000: return 64 / Re
    return 0.25 / (math.log10(eps / (3.7 * D) + 5.74 / Re**0.9)**2)

# Construir interpoladores
Hf, qmin_h, qmax_h = build_interp(head_pts)
Ef, qmin_e, qmax_e = build_interp(eff_pts)
Pf, qmin_p, qmax_p = build_interp(power_pts)
qmin, qmax = max(qmin_h, qmin_e, qmin_p), min(qmax_h, qmax_e, qmax_p)

# -------------------------------
# 1. Cálculo por tramos - acero
# -------------------------------
D = 0.80  # m
eps = 0.045e-3  # rugosidad
A = math.pi * D**2 / 4
V = Q_total / A
Re = V * D / nu

rows = []
hf_cum = [0]
acc_loss = 0

for ID, L, dZ in TRAMOS:
    f = swamee_jain_f(Re, eps, D)
    hf = f * (L / D) * (V**2 / (2 * g))
    acc_loss += hf
    hf_cum.append(acc_loss)
    rows.append({"Tramo": ID, "L": L, "ΔZ": dZ, "hf": hf})

df_tramos = pd.DataFrame(rows)
H_static = sum(r["ΔZ"] for r in rows)
H_loss = sum(r["hf"] for r in rows)
H_total = H_static + H_loss

# -------------------------------
# 2. Selección de bombas por estación
# -------------------------------
estaciones = [
    ("Est1 (2→4)", ["2-3", "3-4"], 930, 7),
    ("Est2 (4→6)", ["4-5", "5-6"], 840, 4),
    ("Est3 (6→9)", ["6-7", "7-8", "8-9"], 656.67, 3),
]

df_est = pd.DataFrame([{
    "Estación": e,
    "Head_m": H,
    "Bombas": N,
    "Q_bomba_Ls": (Q_total * 1000) / N,
    "Power_kW": Pf((Q_total * 1000) / N),
    "Eficiencia(%)": Ef((Q_total * 1000) / N)
} for e, _, H, N in estaciones])

# -------------------------------
# 3. Espesor de tubería (ASME B31.4)
# -------------------------------
SIGMA_y = 448e6  # Pa
F1 = 0.72
sigma_allow = SIGMA_y * F1  # Pa

tramos_est = []
for (ID, _, dZ), (_, _, H_grupo, _) in zip(TRAMOS, estaciones*3):
    P_int = rho * g * H_grupo
    t_req = (P_int * D) / (2 * sigma_allow) * 1000  # mm
    tramos_est.append({"Tramo": ID, "Head diseño": H_grupo, "P bar": P_int/1e5, "t_req_mm": t_req})

df_esp = pd.DataFrame(tramos_est)

# -------------------------------
# 4. Dimensionamiento de estanques
# -------------------------------
vol_tanque = Q_total * t_res
h_tanque = 5
D_tanque = math.sqrt((4 * vol_tanque) / (math.pi * h_tanque))

# -------------------------------
# 5. Gráficos
# -------------------------------
if SAVE_PLOTS:
    # HQ curve
    qx = np.linspace(qmin, qmax, 50)
    HQ = [Hf(q) for q in qx]
    plt.figure()
    plt.plot(qx, HQ)
    plt.scatter([200, 160, 266.7], [840, 890, 656.667])
    plt.title("Curva H-Q bomba Goulds 3600")
    plt.xlabel("Q (L/s)"); plt.ylabel("Head (m)")
    plt.grid(); plt.savefig("curva_HQ.png")

    # Perfil energético
    x_acum = [0] + list(np.cumsum([r["L"] for r in rows]))
    z = [ALT[n] for n in ["2", "3", "4", "5", "6", "7", "8", "9"]]
    E_line = [ALT[n] + hf_cum[i] for i, n in enumerate(["2", "3", "4", "5", "6", "7", "8", "9"])]
    plt.figure()
    plt.plot(x_acum, z, label="Terreno")
    plt.plot(x_acum, E_line, label="Línea Energía")
    plt.legend(); plt.grid()
    plt.xlabel("Distancia (m)"); plt.ylabel("Elevación (m)")
    plt.title("Perfil longitudinal"); plt.savefig("perfil_longitudinal.png")

# -------------------------------
# 6. Exportar resultados
# -------------------------------
with pd.ExcelWriter("sistema_bombeo_ovejeria.xlsx") as writer:
    df_tramos.to_excel(writer, sheet_name="Tramos", index=False)
    df_est.to_excel(writer, sheet_name="Estaciones", index=False)
    df_esp.to_excel(writer, sheet_name="Espesores", index=False)

print("\n=== Modelo completo generado ===")
print(f"- Head total requerido: {H_total:.1f} m")
print(f"- Estanque: volumen={vol_tanque:.1f} m3, diámetro={D_tanque:.2f} m")
print("- Resultados guardados en sistema_bombeo_ovejeria.xlsx")
print("- Gráficos guardados en PNG (si SAVE_PLOTS=True)")

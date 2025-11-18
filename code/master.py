import math
import numpy as np
import pandas as pd

# ============================================================
# 0. PARÁMETROS GLOBALES DEL PROBLEMA
# ============================================================

# Caudal total de diseño
Q_total_Ls = 800.0                 # L/s
Q_total_m3s = Q_total_Ls / 1000.0  # m³/s

# Propiedades del fluido (agua)
rho = 1000.0  # kg/m³
g = 9.81      # m/s²

# Diámetro y factor de fricción de la tubería
D = 0.80      # m (puedes cambiar a otro diámetro)
f = 0.02      # factor de Darcy (supuesto)

# ============================================================
# 1. DATOS DE GEOMETRÍA – TRAMOS Y COTAS
#    Tramos desde Estanque inicio (2) hasta Estanque proceso (9)
# ============================================================

# Largos de ruta (km) y diferencia de cotas (m)
tramos = ["2-3", "3-4", "4-5", "5-6", "6-7", "7-8", "8-9"]
L_km = [23.00, 2.87, 7.84, 8.67, 0.32, 9.90, 5.87]  # km
dZ =   [845,   40,   617,  125,  -18,  170,  375]   # m

L_m = [l * 1000.0 for l in L_km]

# Cotas de puntos relevantes (msnm)
alts = {
    2: 745,
    3: 1590,
    4: 1630,
    5: 2247,
    6: 2372,
    7: 2354,
    8: 2524,
    9: 2899
}

# ============================================================
# 2. CURVAS DE LA BOMBA GOULDS 3600 (DATOS DIGITIZADOS)
#    Q en L/s, H en m, P en kW, η en %
# ============================================================

head_points = [
    (40, 970-400),
    (80, 960-400),
    (160,890-400),
    (200,840-400),
    (280,620-400)
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

# ------------------------------------------------------------
def build_interp(points):
    """
    Crea una función de interpolación lineal con extrapolación suave.
    Si q_new está fuera del rango, extrapola usando la pendiente del extremo.
    """
    pts = sorted(points, key=lambda x: x[0])
    q = np.array([p[0] for p in pts], dtype=float)
    y = np.array([p[1] for p in pts], dtype=float)

    def f(q_new):
        q_new = np.atleast_1d(q_new)
        y_new = np.empty_like(q_new, dtype=float)
        for i, qx in enumerate(q_new):
            if qx <= q[0]:
                slope = (y[1] - y[0]) / (q[1] - q[0])
                y_new[i] = y[0] + slope * (qx - q[0])
            elif qx >= q[-1]:
                slope = (y[-1] - y[-2]) / (q[-1] - q[-2])
                y_new[i] = y[-1] + slope * (qx - q[-1])
            else:
                y_new[i] = np.interp(qx, q, y)
        return y_new if len(y_new) > 1 else y_new[0]

    return f, float(q.min()), float(q.max())



head_interp, qmin_h, qmax_h = build_interp(head_points)
eff_interp,  qmin_e, qmax_e = build_interp(eff_points)
power_interp,qmin_p, qmax_p = build_interp(power_points)
npsh_interp, qmin_n, qmax_n = build_interp(npsh_points)

q_min_curve = max(qmin_h, qmin_e, qmin_p)   # L/s
q_max_curve = min(qmax_h, qmax_e, qmax_p)   # L/s

# ============================================================
# 3. CÁLCULO DE PÉRDIDAS POR FRICCIÓN Y HEAD TOTAL
# ============================================================

A = math.pi * D**2 / 4.0                # área de la tubería
V = Q_total_m3s / A                     # velocidad promedio

hf_segmentos = []
for Li in L_m:
    hf_i = f * (Li / D) * (V**2 / (2.0 * g))
    hf_segmentos.append(hf_i)

hf_total = sum(hf_segmentos)
H_static = sum(dZ)                      # diferencia de cotas 2–9
H_total = H_static + hf_total          # head dinámico total requerido

print("========== PERFIL HIDRÁULICO GLOBAL ==========")
for i, tramo in enumerate(tramos):
    print(f"Tramo {tramo}: L = {L_m[i]:8.1f} m, Δz = {dZ[i]:5.1f} m, hf = {hf_segmentos[i]:6.1f} m")

print(f"\nHead estático total       : {H_static:7.1f} m")
print(f"Pérdidas por fricción tot.: {hf_total:7.1f} m")
print(f"Head dinámico total (TDH) : {H_total:7.1f} m\n")

# ============================================================
# 4. BÚSQUEDA DE ARREGLO DE BOMBAS
#    - N_par: número de bombas en paralelo por estación
#    - N_st : número de estaciones en serie
#    Se evalúan opciones y se elige la de menor potencia total.
# ============================================================

candidatos = []

for N_par in range(1, 10):  # probamos hasta 9 bombas en paralelo
    Q_bomba_Ls = Q_total_Ls / N_par

    # NO filtramos por q_min_curve ni q_max_curve
    # porque ahora sí aceptamos extrapolación
    Hb = float(head_interp(Q_bomba_Ls))
    etab = float(eff_interp(Q_bomba_Ls))
    Pb = float(power_interp(Q_bomba_Ls))  # kW

    N_st = math.ceil(H_total / Hb)        # estaciones mínimas para cubrir el TDH
    H_disponible = N_st * Hb
    P_total = N_par * N_st * Pb           # potencia instalada total

    candidatos.append({
        "N_par": N_par,
        "Q_bomba_Ls": Q_bomba_Ls,
        "H_bomba_m": Hb,
        "eta_%": etab,
        "P_bomba_kW": Pb,
        "N_est": N_st,
        "H_total_disp_m": H_disponible,
        "P_total_kW": P_total
    })

if not candidatos:
    raise RuntimeError("No hay ninguna combinación N_par que caiga dentro de la curva de la bomba.")

df_candidatos = pd.DataFrame(candidatos)
df_candidatos = df_candidatos.sort_values("P_total_kW")

print("========== CANDIDATOS DE ARREGLO DE BOMBAS ==========")
print(df_candidatos.to_string(index=False, 
                              formatters={"Q_bomba_Ls": "{:.1f}".format,
                                          "H_bomba_m": "{:.1f}".format,
                                          "eta_%": "{:.1f}".format,
                                          "P_bomba_kW": "{:.0f}".format,
                                          "H_total_disp_m": "{:.1f}".format,
                                          "P_total_kW": "{:.0f}".format}))

mejor = df_candidatos.iloc[0]
print("\n========== ARREGLO SELECCIONADO (MENOR POTENCIA TOTAL) ==========")
print(f"Bombas en paralelo por estación : {int(mejor['N_par'])}")
print(f"Número de estaciones en serie    : {int(mejor['N_est'])}")
print(f"Caudal por bomba                 : {mejor['Q_bomba_Ls']:.1f} L/s")
print(f"Head por bomba                   : {mejor['H_bomba_m']:.1f} m")
print(f"Eficiencia aproximada            : {mejor['eta_%']:.1f} %")
print(f"Potencia por bomba               : {mejor['P_bomba_kW']:.0f} kW")
print(f"Potencia total instalada         : {mejor['P_total_kW']:.0f} kW")
print(f"Head total disponible            : {mejor['H_total_disp_m']:.1f} m")

# ============================================================
# 5. DESGLOSE DE HEAD POR ESTACIÓN (SUPONIENDO 3 ESTACIONES)
#    Estación 1: de punto 2 a 4 (tramos 2-3 y 3-4)
#    Estación 2: de punto 4 a 6 (tramos 4-5 y 5-6)
#    Estación 3: de punto 6 a 9 (tramos 6-7, 7-8 y 8-9)
# ============================================================

stations_segments = {
    1: [0, 1],        # 2-3, 3-4
    2: [2, 3],        # 4-5, 5-6
    3: [4, 5, 6]      # 6-7, 7-8, 8-9
}

station_nodes = {
    1: (2, 4),
    2: (4, 6),
    3: (6, 9)
}

print("\n========== DESGLOSE POR ESTACIÓN (SUPOSICIÓN 3 ESTACIONES) ==========")
for st in [1, 2, 3]:
    seg_idx = stations_segments[st]
    L_st = sum(L_m[i] for i in seg_idx)
    hf_st = sum(hf_segmentos[i] for i in seg_idx)
    n_ini, n_fin = station_nodes[st]
    dz_st = alts[n_fin] - alts[n_ini]
    H_st = dz_st + hf_st

    print(f"Estación {st}:")
    print(f"  Longitud acumulada        : {L_st:8.1f} m")
    print(f"  Δz (de punto {n_ini} a {n_fin}) : {dz_st:8.1f} m")
    print(f"  Pérdidas por fricción     : {hf_st:8.1f} m")
    print(f"  Head requerido estación   : {H_st:8.1f} m\n")

# ============================================================
# 6. OPCIONAL: GUARDAR TABLA DE CANDIDATOS A CSV
# ============================================================

df_candidatos.to_csv("candidatos_bombas1.csv", index=False)
print("Archivo 'candidatos_bombas1.csv' generado.")

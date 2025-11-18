#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import pandas as pd

# ==========================================
# 1. Datos globales
# ==========================================
rho = 1000.0       # kg/m3
g   = 9.81         # m/s2

# Diámetro exterior de la tubería (ASME usa DOD)
D   = 0.80         # m

# Parámetros de material API 5L X65 según ASME B31.4
Sy_MPa = 448.0          # límite de fluencia (MPa)
F1     = 0.72           # factor de diseño hoop para pipeline (tabla A402.3.5(a))
sigma_allow = F1 * Sy_MPa * 1e6   # Pa, tensión admisible hoop = F1 * Sy

# Heads aportados por cada estación (m)
H_est1 = 930.0          # estación 1 (7 bombas)
H_est2 = 840.0          # estación 2 (4 bombas)
H_est3 = 656.667        # estación 3 (3 bombas)

# Head acumulado máximo después de cada estación
H_acum_1 = H_est1
H_acum_2 = H_est2
H_acum_3 = H_est3

# ==========================================
# 2. Tramos de la línea de impulsión
# ==========================================
tramos = [
    {"id": "2-3", "grupo": "Estación 1", "H_diseno_m": H_acum_1},
    {"id": "3-4", "grupo": "Estación 1", "H_diseno_m": H_acum_1},
    {"id": "4-5", "grupo": "Estación 2", "H_diseno_m": H_acum_2},
    {"id": "5-6", "grupo": "Estación 2", "H_diseno_m": H_acum_2},
    {"id": "6-7", "grupo": "Estación 3", "H_diseno_m": H_acum_3},
    {"id": "7-8", "grupo": "Estación 3", "H_diseno_m": H_acum_3},
    {"id": "8-9", "grupo": "Estación 3", "H_diseno_m": H_acum_3},
]

# Espesores adoptados (mm) por tramo
e_adopt_mm = {
    "2-3": 32.0,
    "3-4": 32.0,
    "4-5": 50.0,
    "5-6": 50.0,
    "6-7": 70.0,
    "7-8": 70.0,
    "8-9": 70.0,
}

# ==========================================
# 3. Cálculo de presiones y espesores
# ==========================================
rows = []
for tr in tramos:
    tramo_id = tr["id"]
    H_d = tr["H_diseno_m"]                # m de columna de agua
    P_pa = rho * g * H_d                  # Pa
    P_bar = P_pa / 1e5                    # bar

    # Espesor mínimo según ASME B31.4 (hoop)
    e_req_m  = (P_pa * D) / (2.0 * sigma_allow)  # m
    e_req_mm = e_req_m * 1000.0                  # mm

    # Espesor adoptado
    e_ad_mm = e_adopt_mm.get(tramo_id, e_req_mm)
    e_ad_m  = e_ad_mm / 1000.0

    # Hoop stress real con espesor adoptado
    Sh_adopt_Pa  = (P_pa * D) / (2.0 * e_ad_m)   # Pa
    Sh_adopt_MPa = Sh_adopt_Pa / 1e6

    util_e     = e_req_mm / e_ad_mm if e_ad_mm > 0 else None
    util_hoop  = Sh_adopt_Pa / sigma_allow if sigma_allow > 0 else None

    rows.append({
        "Tramo": tramo_id,
        "Grupo estación": tr["grupo"],
        "H diseño (m)": H_d,
        "P interna (bar)": P_bar,
        "e_req (mm) ASME": e_req_mm,
        "e_adopt (mm)": e_ad_mm,
        "Utilización espesor (%)": util_e * 100.0 if util_e is not None else None,
        "Hoop stress adoptada (MPa)": Sh_adopt_MPa,
        "Tensión admisible (MPa)": sigma_allow / 1e6,
        "Utilización esfuerzo (%)": util_hoop * 100.0 if util_hoop is not None else None,
    })

df = pd.DataFrame(rows)

# Ordenar por tramo
df = df.set_index("Tramo").loc[["2-3","3-4","4-5","5-6","6-7","7-8","8-9"]].reset_index()

# Mostrar en consola
print(df.to_string(index=False))

# Guardar como Excel
excel_path = "espesores_api5lx65_tramos_ASME.xlsx"
with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
    df.to_excel(writer, sheet_name="Espesores", index=False)

print(f"\nArchivo Excel '{excel_path}' generado con éxito.")

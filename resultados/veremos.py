#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from openpyxl import Workbook
import os


# =========================================================
# 1. DATOS GLOBALES
# =========================================================
rho = 1000          # kg/m³ (agua)
g = 9.81            # m/s²
nu = 1e-6           # viscosidad cinemática
Q_total = 0.8       # m³/s (800 L/s)
D = 0.80            # m diámetro interno
roughness = 0.045e-3  # rugosidad para acero

# Estaciones de bombeo: 7,4,3 bombas con curva de fábrica
bombas_por_estacion = [7, 4, 3]

# Head por bomba desde curva digitizada
head_points = [(40, 970), (80, 960), (160, 890), (200, 840), (280, 620)]
eff_points  = [(40, 33), (80, 56), (160, 81), (220, 85), (280, 79)]
power_points= [(40,1200), (80,1400), (160,1750), (200,1950), (260,2150), (280,3400)]

def interpolate(xy, q):
    xs, ys = zip(*xy)
    if q < xs[0]: return ys[0]
    if q > xs[-1]: return ys[-1]
    return float(np.interp(q, xs, ys))

# =========================================================
# 2. TRAMOS Y COTAS
# =========================================================
TRAMOS = [
    {"id": "2-3", "L": 23000, "dZ": 845, "grupo": "Est.1"},
    {"id": "3-4", "L": 2870,  "dZ": 40,  "grupo": "Est.1"},
    {"id": "4-5", "L": 7840,  "dZ": 617, "grupo": "Est.2"},
    {"id": "5-6", "L": 8670,  "dZ": 125, "grupo": "Est.2"},
    {"id": "6-7", "L": 320,   "dZ": -18, "grupo": "Est.3"},
    {"id": "7-8", "L": 9900,  "dZ": 170, "grupo": "Est.3"},
    {"id": "8-9", "L": 5870,  "dZ": 375, "grupo": "Est.3"},
]

# =========================================================
# 3. FUNCIONES AUXILIARES
# =========================================================
def swamee_jain_f(Re, eD):
    if Re < 2000: return 64 / Re
    return 0.25 / (math.log10(eD/3.7 + 5.74/Re**0.9)**2)

def calcular_head_bomba(Q_Ls, Npar):
    Q_bomba = Q_Ls / Npar
    H = interpolate(head_points, Q_bomba)
    eta = interpolate(eff_points, Q_bomba)
    Pw = interpolate(power_points, Q_bomba)
    return H, eta, Pw

# =========================================================
# 4. CÁLCULO HIDRÁULICO POR TRAMO
# =========================================================
rows_tramos = []
V = Q_total / (math.pi * D**2 / 4)
Re = V * D / nu

for i, tr in enumerate(TRAMOS):
    f = swamee_jain_f(Re, roughness/D)
    hf = f * (tr['L'] / D) * (V**2 / (2*g))
    rows_tramos.append({
        **tr, "V": V, "Re": Re, "f": f, "hf": hf
    })

df_tramos = pd.DataFrame(rows_tramos)

# Head total por estación y acumulado
H_estaciones = {}
head_acum = 0
for est, Npar in zip(["Est.1", "Est.2", "Est.3"], bombas_por_estacion):
    H_bomba, _, _ = calcular_head_bomba(800, Npar)
    H_estaciones[est] = H_bomba
    head_acum += H_bomba

# =========================================================
# 5. ESPESORES (ASME B31.4, API 5L X65)
# =========================================================
Sy = 448e6         # Pa
F1 = 0.72          # ASME pipeline factor
sigma_allow = Sy * F1
rows_esp = []
for tr in df_tramos.itertuples():
    P = rho * g * H_estaciones[tr.grupo]
    e_req = (P * D) / (2 * sigma_allow) * 1000
    e_ad = [32,50,70][["Est.1","Est.2","Est.3"].index(tr.grupo)]
    hoop = (P * D / (2*(e_ad/1000))) / 1e6
    rows_esp.append({
        "Tramo": tr.id, "Grupo": tr.grupo,
        "P_bar": P/1e5, "e_req_mm": e_req,
        "e_adopt_mm": e_ad, "hoop_MPa": hoop,
        "util(%)": (e_req/e_ad)*100
    })
df_esp = pd.DataFrame(rows_esp)

# =========================================================
# 6. ESTANQUES (30 min autonomía)
# =========================================================
t_aut = 30 * 60
V_tanque = Q_total * t_aut
h_tanque = 5.0
D_eq = math.sqrt(4*V_tanque/(math.pi*h_tanque))
df_est = pd.DataFrame([{
    "Volumen m3": V_tanque, "Altura m": h_tanque, "Diámetro m": D_eq
}])

# =========================================================
# 7. GRÁFICOS
# =========================================================
plt.figure()
x = np.cumsum([0]+[t['L'] for t in TRAMOS])
z = np.cumsum([0]+[t['dZ'] for t in TRAMOS])
plt.plot(x, z, label="Perfil")
plt.xlabel("Distancia (m)")
plt.ylabel("Elevación (m)")
plt.title("Perfil longitudinal")
plt.grid()
plt.savefig("perfil_longitudinal.png")

# =========================================================
# 8. EXPORTAR A EXCEL
# =========================================================
with pd.ExcelWriter("resultado_integrado.xlsx") as writer:
    df_tramos.to_excel(writer, sheet_name="Tramos", index=False)
    df_esp.to_excel(writer,   sheet_name="Espesores", index=False)
    pd.DataFrame(H_estaciones.items(), columns=["Estación","Head(m)"]).to_excel(writer, sheet_name="Head bombas", index=False)
    df_est.to_excel(writer,   sheet_name="Estanques", index=False)

# =========================================================
# 9. GENERAR PDF
# =========================================================
def gen_pdf():
    doc = SimpleDocTemplate("Informe_TranqueOvejeria.pdf", pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Informe Técnico – Sistema de Impulsión</b>", styles['Title']))
    story.append(Paragraph("Tranque Ovejería – Modelación integrada.", styles['Normal']))
    story.append(Spacer(1,8))

    story.append(Paragraph("<b>Head por estación:</b>", styles['Heading2']))
    for est,H in H_estaciones.items():
        story.append(Paragraph(f"{est}: {H:.1f} m", styles['Normal']))

    story.append(Paragraph("<b>Espesores críticos:</b>", styles['Heading2']))
    for _,r in df_esp.iterrows():
        story.append(Paragraph(f"{r.Tramo}: requerido {r.e_req_mm:.1f} mm, adoptado {r.e_adopt_mm} mm", styles['Normal']))

    if os.path.exists("perfil_longitudinal.png"):
        story.append(Image("perfil_longitudinal.png", width=400, height=300))

    doc.build(story)

gen_pdf()

print(">> Modelo completo generado:\n- resultado_integrado.xlsx\n- Informe_TranqueOvejeria.pdf\n- perfil_longitudinal.png")

# ==== Parámetros generales ====
Q_total = 0.8        # m³/s
V_max = 2.0          # m/s velocidad máxima recomendada
t_aut = 10 * 60      # segundos de autonomía del estanque (10 min)
K_minor = 0.5        # pérdidas menores (coeficiente promedio)
rho = 1000           # kg/m³
g = 9.81             # m/s²

# ==== Materiales ====
MATERIALES = {
    "acero":    {"eps": 0.045e-3, "sigma_adm": 150e6},  # rugosidad, tensión admisible (Pa)
    "hormigon": {"eps": 0.3e-3,   "sigma_adm": 20e6}
}
TRAMOS = [
    {"id": "2-3", "L": 23000, "dZ": 845, "material": "hormigon"},
    {"id": "3-4", "L": 2870,  "dZ": 40,  "material": "acero"},
    {"id": "4-5", "L": 7840,  "dZ": 617, "material": "acero"},
    {"id": "5-6", "L": 8670,  "dZ": 125, "material": "acero"},
    {"id": "6-7", "L": 320,   "dZ": -18, "material": "hormigon"},
    {"id": "7-8", "L": 9900,  "dZ": 170, "material": "hormigon"},
    {"id": "8-9", "L": 5870,  "dZ": 375, "material": "hormigon"},
]

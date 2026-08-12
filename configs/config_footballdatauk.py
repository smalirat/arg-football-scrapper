import pandas as pd

# MAPEO_EQUIPOS: Se mantiene tu lista original (No la toco)
MAPEO_EQUIPOS = {
    'Aldosivi': 0, 'All Boys': 1, 'Argentinos Jrs': 7, 'Arsenal Sarandi': 8,
    'Atl. Rafaela': 10, 'Atl. Tucuman': 11, 'Banfield': 14, 'Barracas Central': 95,
    'Belgrano': 16, 'Boca Juniors': 17, 'Central Cordoba': 19, 'Chacarita Juniors': 21,
    'Colon Santa FE': 25, 'Colon Santa Fe': 25,
    'Defensa y Justicia': 27, 'Estudiantes L.P.': 37,
    'Gimnasia L.P.': 43, 'Godoy Cruz': 46, 'Huracan': 48, 'Ind. Rivadavia': 55, 
    'Independiente': 56, 'Instituto': 57, 'Lanus': 63, 'Newells Old Boys': 66, 
    'Olimpo Bahia Blanca': 68, 'Patronato': 69, 'Platense': 70, 'Quilmes': 71, 
    'Racing Club': 73, 'River Plate': 75, 'Rosario Central': 76, 'San Lorenzo': 77, 
    'San Martin S.J.': 80, 'San Martin T.': 81, 'Sarmiento Junin': 84, 
    'Talleres Cordoba': 88, 'Temperley': 90, 'Tigre': 91, 'Union de Santa Fe': 93, 
    'Velez Sarsfield': 94, 'Crucero del Norte': 26, 'Estudiantes Rio Cuarto': 38, 
    'Gimnasia Mendoza': 44, 'Nueva Chicago': 67, 'Dep. Riestra': 102
}

def obtener_ids_edicion_especiales(season_csv, fecha_str):
    partes = fecha_str.split('/')
    mes = int(partes[1])
    anio = int(partes[2])

    if season_csv == "2013/2014":
        return [123, 124, 125]

    if anio == 2023:
        return [137] if mes <= 7 else [138]
    
    if anio == 2024:
        return [139] if mes <= 5 else [140]
    
    if anio == 2025:
        return [141] if mes <= 6 else [142]
    
    if anio == 2026:
        return [143] if mes <= 6 else [144]

    return None

def clean_nan(val):
    return None if pd.isna(val) else val
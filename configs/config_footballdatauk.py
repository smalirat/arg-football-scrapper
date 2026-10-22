import pandas as pd

# MAPEO_EQUIPOS: nombre en el CSV de Football-Data -> IDs del equipo en la base.
# Cada equipo tiene dos IDs porque los partidos vienen de dos fuentes:
#   kaggle: partidos históricos (hasta 2023), cargados desde el CSV de Kaggle
#   fotmob: partidos desde 2024, cargados desde FotMob
# Los IDs de FotMob se verificaron cruzando las filas de 2024/2026 con los
# partidos de la base por fecha y resultado (todos los cruces coincidieron).
# None = el equipo no tiene partidos de esa fuente en primera.
MAPEO_EQUIPOS = {
    'Aldosivi': {'kaggle': 0, 'fotmob': 161728},
    'All Boys': {'kaggle': 1, 'fotmob': None},
    'Argentinos Jrs': {'kaggle': 7, 'fotmob': 10086},
    'Arsenal Sarandi': {'kaggle': 8, 'fotmob': None},
    'Atl. Rafaela': {'kaggle': 10, 'fotmob': None},
    'Atl. Tucuman': {'kaggle': 11, 'fotmob': 161727},
    'Banfield': {'kaggle': 14, 'fotmob': 10087},
    'Barracas Central': {'kaggle': 95, 'fotmob': 213534},
    'Belgrano': {'kaggle': 16, 'fotmob': 10092},
    'Boca Juniors': {'kaggle': 17, 'fotmob': 10077},
    'Central Cordoba': {'kaggle': 19, 'fotmob': 213596},
    'Chacarita Juniors': {'kaggle': 21, 'fotmob': None},
    'Colon Santa FE': {'kaggle': 25, 'fotmob': None},
    'Colon Santa Fe': {'kaggle': 25, 'fotmob': None},
    'Crucero del Norte': {'kaggle': 26, 'fotmob': None},
    'Defensa y Justicia': {'kaggle': 27, 'fotmob': 161730},
    'Dep. Riestra': {'kaggle': None, 'fotmob': 298629},
    'Estudiantes L.P.': {'kaggle': 37, 'fotmob': 10094},
    'Estudiantes Rio Cuarto': {'kaggle': 38, 'fotmob': 213591},
    'Gimnasia L.P.': {'kaggle': 43, 'fotmob': 10103},
    'Gimnasia Mendoza': {'kaggle': 44, 'fotmob': 568727},
    'Godoy Cruz': {'kaggle': 46, 'fotmob': 10227},
    'Huracan': {'kaggle': 48, 'fotmob': 10081},
    'Ind. Rivadavia': {'kaggle': 55, 'fotmob': 161729},
    'Independiente': {'kaggle': 56, 'fotmob': 10078},
    'Instituto': {'kaggle': 57, 'fotmob': 10090},
    'Lanus': {'kaggle': 63, 'fotmob': 10082},
    'Newells Old Boys': {'kaggle': 66, 'fotmob': 10201},
    'Nueva Chicago': {'kaggle': 67, 'fotmob': None},
    'Olimpo Bahia Blanca': {'kaggle': 68, 'fotmob': None},
    'Patronato': {'kaggle': 69, 'fotmob': None},
    'Platense': {'kaggle': 70, 'fotmob': 10089},
    'Quilmes': {'kaggle': 71, 'fotmob': None},
    'Racing Club': {'kaggle': 73, 'fotmob': 10080},
    'River Plate': {'kaggle': 75, 'fotmob': 10076},
    'Rosario Central': {'kaggle': 76, 'fotmob': 10084},
    'San Lorenzo': {'kaggle': 77, 'fotmob': 10083},
    'San Martin S.J.': {'kaggle': 80, 'fotmob': None},
    'San Martin T.': {'kaggle': 81, 'fotmob': None},
    'Sarmiento Junin': {'kaggle': 84, 'fotmob': 202757},
    'Talleres Cordoba': {'kaggle': 88, 'fotmob': 10101},
    'Temperley': {'kaggle': 90, 'fotmob': None},
    'Tigre': {'kaggle': 91, 'fotmob': 89396},
    'Union de Santa Fe': {'kaggle': 93, 'fotmob': 10096},
    'Velez Sarsfield': {'kaggle': 94, 'fotmob': 10079},
}

# Ediciones de primera división contra las que se cruza el CSV (por temporada)
PREFIJOS_EDICION = ('Liga Profesional', 'Copa de la Liga Profesional')


def ids_equipo(nombre_csv):
    """Todos los equipo_id posibles de un nombre del CSV (Kaggle y/o FotMob)."""
    ids = MAPEO_EQUIPOS.get(nombre_csv) or {}
    return {i for i in ids.values() if i is not None}


def clean_nan(val):
    return None if pd.isna(val) else val

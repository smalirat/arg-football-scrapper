# Equivalencia de los IDs de equipo del CSV de Kaggle con los de FotMob.
#
# El CSV histórico numera los equipos del 0 al 95 y FotMob tiene sus propios
# IDs. Si se cargaran los dos tal cual, cada club quedaría duplicado en la base
# (pasó: se corrigió con la migración 0005_fusion_equipos de argstats/db).
# Por eso los scripts traducen el ID de Kaggle al de FotMob antes de escribir.
#
# Los IDs de Kaggle que no están acá son clubes que FotMob no tiene (por
# ejemplo Mandiyú o Loma Negra): se cargan con su ID de Kaggle.

KAGGLE_A_FOTMOB = {
     0: 161728,  # Aldosivi -> Aldosivi
     1: 161732,  # All Boys -> All Boys
     2: 10099,   # Almagro -> Almagro
     3: 568715,  # Altos Hornos Zapla -> Altos Hornos Zapla
     4: 354496,  # Alvarado -> CA Alvarado
     5: 568711,  # Andino (LR) -> Andino
     7: 10086,   # Argentinos -> Argentinos Juniors
     8: 10098,   # Arsenal -> Arsenal Sarandi
    10: 10085,   # Atl Rafaela -> Atletico Rafaela
    11: 161727,  # Atl Tucuman -> Atlético Tucumán
    13: 213525,  # Atlanta -> Atlanta
    14: 10087,   # Banfield -> Banfield
    15: 1723191, # Bartolome Mitre (M) -> CA Bartolome Mitre
    16: 10092,   # Belgrano -> Belgrano
    17: 10077,   # Boca Juniors -> Boca Juniors
    18: 279383,  # Central Cba (R) -> Central Cordoba de Rosario
    19: 213596,  # Central Cba (SdE) -> Central Córdoba de Santiago
    20: 213597,  # Central Norte (S) -> Central Norte
    21: 10093,   # Chacarita -> Chacarita Juniors
    22: 465716,  # Chaco For Ever -> CA Chaco For Ever
    23: 213539,  # Cipolletti -> Club Cipolletti
    24: 1076357, # Circulo Dep. (O) -> Circulo Deportivo
    26: 213598,  # Crucero (M) -> Crucero del Norte
    27: 161730,  # Def y Justicia -> Defensa y Justicia
    28: 213603,  # Def. de Belgrano -> CA Defensores de Belgrano
    30: 213527,  # Dep. Armenio -> Deportivo Armenio
    31: 213538,  # Dep. Español -> Deportivo Espanol
    32: 213530,  # Dep. Moron -> Deportivo Moron
    33: 568707,  # Dep. Roca -> Deportivo Roca
    34: 213594,  # Desamparados -> Desamparados
    36: 213523,  # Estudiantes (BA) -> Club Atlético Estudiantes
    37: 10094,   # Estudiantes (LP) -> Estudiantes
    38: 213591,  # Estudiantes (RC) -> Estudiantes de Río Cuarto
    40: 161733,  # Ferro -> Ferro Carril Oeste
    41: 213599,  # Gimnasia (CdU) -> Gimnasia y Esgrima de Concepcion
    42: 10095,   # Gimnasia (J) -> Gimnasia Jujuy
    43: 10103,   # Gimnasia (LP) -> Gimnasia LP
    44: 568727,  # Gimnasia (M) -> Gimnasia Mendoza
    45: 276511,  # Gimnasia (S) -> Gimnasia y Tiro
    46: 10227,   # Godoy Cruz -> Godoy Cruz
    47: 354516,  # Guarani (M) -> Guarani Antonio Franco
    48: 10081,   # Huracan -> Huracán
    52: 616460,  # Huracan (LH) -> Huracan Las Heras
    54: 206421,  # Huracan (TA) -> Huracan Tres Arroyos
    55: 161729,  # Ind Rivadavia -> Independiente Rivadavia
    56: 10078,   # Independiente -> Independiente
    57: 10090,   # Instituto -> Instituto
    60: 213600,  # Juv. Antoniana -> Juventud Antoniana
    61: 213588,  # Juv. Unida (SL) -> Juventud Unida Universitario
    62: 1618060, # Kimberley (MdP) -> Kimberley
    63: 10082,   # Lanus -> Lanús
    65: 10097,   # Los Andes -> Los Andes
    66: 10201,   # Newells -> Newell's Old Boys
    67: 10091,   # Nueva Chicago -> Nueva Chicago
    68: 10100,   # Olimpo -> Olimpo
    69: 207875,  # Patronato -> Patronato de Parana
    70: 10089,   # Platense -> Club Atlético Platense
    71: 10226,   # Quilmes -> Quilmes
    72: 213592,  # Racing (C) -> Racing de Cordoba
    73: 10080,   # Racing Club -> Racing Club
    75: 10076,   # River Plate -> River Plate
    76: 10084,   # Rosario Central -> Rosario Central
    77: 10083,   # San Lorenzo -> San Lorenzo
    79: 1442518, # San Martin (M) -> San Martin Mendoza
    80: 89395,   # San Martin (SJ) -> San Martin San Juan
    81: 146371,  # San Martin (T) -> San Martin de Tucuman
    82: 213522,  # San Telmo -> San Telmo
    83: 203830,  # Santamarina -> Santamarina
    84: 202757,  # Sarmiento (J) -> Sarmiento
    85: 298640,  # Sarmiento (R) -> Sarmiento de Resistencia
    87: 213533,  # Sp. Italiano -> Sportivo Italiano
    88: 10101,   # Talleres (C) -> Talleres
    89: 581805,  # Talleres (RdE) -> CA Talleres Remedios de Escalada
    90: 213531,  # Temperley -> Temperley
    91: 89396,   # Tigre -> Tigre
    92: 10102,   # Tiro Federal (R) -> Tiro Federal Rosario
    93: 10096,   # Union -> Unión
    94: 10079,   # Velez -> Vélez Sarsfield
    95: 213534,  # Barracas Central -> Barracas Central
}


def equipo_id(id_kaggle):
    """ID con el que se guarda en la base un equipo del CSV de Kaggle."""
    return KAGGLE_A_FOTMOB.get(int(id_kaggle), int(id_kaggle))

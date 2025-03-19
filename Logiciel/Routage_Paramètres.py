import re
import sys
import os
from datetime import datetime, timedelta

"PARAMETRES DE NAVIGATION"

"TRAVERSEE ATLANTIQUE"
# position_finale, position_initiale = ((-1.8390148914037843, 46.468986830218), (-15.44764920293199, 44.793006205066064)) 
# bg = (37.751188312991886, -74.80351747265776)
# hd = (61.24779029169383, -0.7117176270096285)

"BRETAGNE"
position_initiale, position_finale = ((48.85725806451613, -3.9306451612903226), (47.307795698924735, -2.919354838709677))
bg = (46, -7)
hd = (49, -1.5)

"GOLF DE GASCOGNE"
# position_initiale, position_finale = ((48.85725806451613, -3.9306451612903226), (47.307795698924735, -2.919354838709677))
# bg = (43, -9.5)
# hd = (48.9, -0.9)

"MEDITERRANNEE"
# position_initiale, position_finale = ((4.449957059919272, 43.03482228137273), (7.750689156750921, 39.763423641448114))
# bg = (38.07650729398917, -0.8543382853154504)
# hd = (43.585020563003646, 9.390756905813463)

"BAIE DE QUIBERON"
# position_initiale, position_finale = ((47.51947360133281, -3.02934453657029), (47.29641627857444, -3.3177356614143387))
# bg = (47.19946468891098, -3.405626289938239)
# hd = (47.64175257800393, -2.806871383119167)

"Atlantique centrale"
# position_initiale, position_finale = ((12.75, -33.1), (24.33, -32.80))
# bg = (10, -43)
# hd = (31, -11)

cadre_navigation = (bg, hd)
loc_nav = [bg[1], hd[1], bg[0], hd[0]]

points = [position_initiale, position_finale]

pas_temporel = 0.25
pas_angle = 10


heure_initiale = 12
date_initiale = "0319" # MMJJ

tolerance = 0.0001
rayon_elemination = 0.2

skip = 5
skip_vect_vent = 5

tolerance_arrivée = 100

land_contact = False

enregistrement = False
enregistrement_live = False

live = True
print_données = True
data_route = True
enveloppe = True


drapeau = True

# FICHIER METEO, TERRE
vent = r"Données_vent\METEOCONSULT12Z_VENT_0319_Nord_Atlantique.grb"
new = True
nb_step = 0

excel_wind = r'Logiciel\Données_vent\Vent.xlsx'

type = 'grib'

# Lieu enregistrement image à enregistrer
output_dir = r'C:\Users\arthu\OneDrive\Arthur\Programmation\TIPE_Arthur_Lhoste\images_png'

# PARAMETRES POUR LA POLAIRE
delimeter = r';'  # r'\s+' si Sunfastpol sinon r';'  pour Imoca 
polaire = r'Polaire\Imoca2.pol'


"PARAMETRES VISUELS"

wind_speed_bins = [0, 2, 6, 10, 14, 17, 21, 25, 29, 33, 37, 41, 44, 47, 52, 56, 60]
colors_windy = [
    "#6271B7", "#39619F", "#4A94A9", "#4D8D7B", "#53A553", "#359F35",
    "#A79D51", "#9F7F3A", "#A16C5C", "#813A4E", "#AF5088", "#754A93",
    "#6D61A3", "#44698D", "#5C9098", "#5C9098"
]
colors_météo_marine = [
    "#A7FF91", "#A7FF91", "#75FF52", "#C1FF24", "#FBFD00", "#FEAB00",
    "#FF7100", "#FD5400", "#F80800", "#813A4E", "#AF5088", "#754A93",
    "#6D61A3", "#44698D", "#5C9098", "#5C9098"
]

def disable_prints():
    sys.stdout = open(os.devnull, 'w')

def enable_prints():
    sys.stdout = sys.__stdout__
    
# Extraction de l'heure et de la date du GRIB
match = re.search(r'(\d+)Z.*?_(\d{4})_', vent)

if match:
    heure_grib = int(match.group(1))  # Nombre avant "Z"
    date_grib = match.group(2)  # 4 chiffres correspondant à la date
    # print(f"L'heure initiale est : {heure_grib}")
    # print(f"La date initiale du GRIB est : {date_grib}")
else:
    pass
try:
    # Date et heure initiales du GRIB
    date_heure_grib = datetime.strptime(date_grib, "%m%d") + timedelta(hours=heure_grib)

    # Date et heure données en entrée
    date_heure_initiale = datetime.strptime(date_initiale, "%m%d") + timedelta(hours=heure_initiale)

    # Calcul de la différence en heures
    heure_début = int((date_heure_initiale - date_heure_grib).total_seconds() / 3600)

    # print(f"L'heure de début (différence en heures) est : {heure_début}")
except ValueError as e:
    print(f"Erreur dans le format des dates ou des heures : {e}")

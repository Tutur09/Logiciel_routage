import numpy as np
import pandas as pd
import math
from time import time
import matplotlib.pyplot as plt
from matplotlib.path import Path

import alphashape
from shapely.geometry import Point, MultiPoint, MultiPolygon, Polygon
from cartopy import crs as ccrs, feature as cfeature

import Routage_Vent as rv
import Routage_Paramètres as p
import Routage_Enveloppe_Concave as envconc
import Routage_Coastline as rc

from concurrent.futures import ThreadPoolExecutor

def projection(position, cap, distance):
    lat_ini = position[0]    
    long_ini = position[1]
    
    
    R = 3440.0
    
    lat_ini_rad = math.radians(lat_ini)
    long_ini_rad = math.radians(long_ini)
    
    bearing_rad = math.radians(cap)
    
    distance_ratio = distance / R
    
    new_lat_rad = math.asin(math.sin(lat_ini_rad) * math.cos(distance_ratio) + 
                            math.cos(lat_ini_rad) * math.sin(distance_ratio) * math.cos(bearing_rad))
    
    new_long_rad = long_ini_rad + math.atan2(math.sin(bearing_rad) * math.sin(distance_ratio) * math.cos(lat_ini_rad),
                                             math.cos(distance_ratio) - math.sin(lat_ini_rad) * math.sin(new_lat_rad))
    
    new_lat = math.degrees(new_lat_rad)
    new_lon = math.degrees(new_long_rad)
    
    return (new_lat, new_lon)

def prochains_points(position, pol_v_vent, d_vent, pas_temporel, pas_angle):
    liste_points = []

    chemin = list(range(0, 360, pas_angle))
    for angle in chemin:
        v_bateau = recup_vitesse_fast(pol_v_vent, d_vent - angle)
        liste_points.append(projection(position, angle, v_bateau * pas_temporel))

    return liste_points

def traiter_point(lat, lon, pas_temporel, pas_angle, heure, filtrer_par_distance):
    parent_point = (lat, lon)

    v_vent, d_vent = rv.get_wind_at_position(lat, lon, heure)
    pol_v_vent = polaire(v_vent)

    enfants = prochains_points(parent_point, pol_v_vent, d_vent, pas_temporel, pas_angle)

    if filtrer_par_distance:
        # Filtrage par distance et limites du cadre de navigation
        enfants = [enfant for enfant in enfants if (enfant[1] <= p.cadre_navigation[1][1] 
                                                    and enfant[1] >= p.cadre_navigation[0][1]
                                                    and enfant[0] <= p.cadre_navigation[1][0]
                                                    and enfant[0] >= p.cadre_navigation[0][0])]

        if p.land_contact:
            enfants = [enfant for enfant in enfants if rc.get_point_value(enfant) == 0]
                    #    if plus_proche_que_parent(p.position_finale, parent_point, enfant)
                    #    and rc.get_point_value(enfant) == 0]
        else:
            enfants = [enfant for enfant in enfants] 
                    #    if plus_proche_que_parent(p.position_finale, parent_point, enfant)]

    return [parent_point, enfants]

def prochains_points_liste_parent_enfants(liste, pas_temporel, pas_angle, heure, filtrer_par_distance=True):
    # Utilisation d’un ThreadPoolExecutor pour paralléliser les opérations
    with ThreadPoolExecutor() as executor:
        # On lance en parallèle le traitement de chaque point de la liste
        futures = [executor.submit(traiter_point, lat, lon, pas_temporel, pas_angle, heure, filtrer_par_distance) 
                   for lat, lon in liste]

        # On récupère les résultats quand ils sont prêts
        liste_rendu = [f.result() for f in futures]

    return liste_rendu

def plus_proche_que_parent(point_arrivee, pos_parent, pos_enfant):
    distance_parent = math.sqrt((point_arrivee[0] - pos_parent[0])**2 + (point_arrivee[1] - pos_parent[1])**2)
    distance_enfant = math.sqrt((point_arrivee[0] - pos_enfant[0])**2 + (point_arrivee[1] - pos_enfant[1])**2)
    return distance_enfant < distance_parent

def polaire(vitesse_vent):
    liste_vitesse = polaire_df.columns

    i = 0
    while i < len(liste_vitesse):
        vitesse = float(liste_vitesse[i])
        if vitesse == vitesse_vent:
            return polaire_df[liste_vitesse[i]]
        elif vitesse > vitesse_vent:
            inf = i - 1
            sup = i
            t = (vitesse_vent - float(liste_vitesse[inf])) / (float(liste_vitesse[sup]) - float(liste_vitesse[inf]))
            return t * polaire_df[liste_vitesse[inf]] + (1 - t) * polaire_df[liste_vitesse[sup]]
        i += 1
    print('Erreur vitesse de vent')
    return None

def recup_vitesse_fast(pol_v_vent, angle):
    if pol_v_vent is None:
        raise ValueError("Erreur : pol_v_vent est None, vérifiez la vitesse du vent.")
    
    angle = abs(angle)
    if angle > 180:
        angle = 360 - angle

    # liste_angle = pol_v_vent.index

    i = 0
    while i < len(pol_v_vent):
        angle_vent = float(liste_angle[i])
        if angle == angle_vent:
            return pol_v_vent[liste_angle[i]]
        elif angle_vent > angle:
            inf = i - 1
            sup = i
            t = (angle - float(liste_angle[inf])) / (float(liste_angle[sup]) - float(liste_angle[inf]))
            return t * pol_v_vent[liste_angle[inf]] + (1 - t) * pol_v_vent[liste_angle[sup]]
        i += 1
    print('Erreur angle')
    return None

def flatten_list(nested_list):
    flattened_list = []
    
    def _flatten(element):
        if isinstance(element, list):
            for item in element:
                _flatten(item)
        else:
            flattened_list.append(element)
    
    _flatten(nested_list)
    return flattened_list

def flatten_list_fast(nested_list):
    flattened_list = []
    stack = [nested_list]

    while stack:
        current = stack.pop()
        if isinstance(current, list):  # Si c'est une liste, on ajoute ses éléments à la pile
            stack.extend(current)
        elif isinstance(current, tuple):  # Si c'est un tuple, on l'ajoute au résultat
            flattened_list.append(current)
    
    return flattened_list

def distance(point1, point2):
    return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def dist_bateau_point(points, point_final, n):
    lat_final, lon_final = point_final
    for (lat, lon) in points:
        distance = math.sqrt((lat - lat_final) ** 2 + (lon - lon_final) ** 2)
        if distance <= n:
            return True    
    return False
    
def plot_point_live(ax, enveloppe_concave, parent_map, position_initiale, position_finale, step_index, loc, couleur='blue'):
    # Effacer uniquement les vecteurs de vent et les chemins, mais garder les enveloppes
    for artist in ax.collections:
        if artist.get_label() != 'Enveloppe actuelle':  # Ne pas supprimer l'enveloppe
            artist.remove()
    
    for line in ax.lines:
        if line.get_label() == 'Route':  # Supprimer le chemin idéal
            line.remove()

    rv.plot_wind(ax, loc, step_indices=[step_index])

    # Vérifier que l'enveloppe est bien une liste de points valides
    if not isinstance(enveloppe_concave, list) or not all(isinstance(point, (list, tuple)) and len(point) == 2 for point in enveloppe_concave):
        print(f"L'enveloppe est invalide : {enveloppe_concave}")
        return

    # Tracer l'enveloppe concave
    hull_lat, hull_lon = zip(*enveloppe_concave)
    # ax.plot(hull_lon + (hull_lon[0],), hull_lat + (hull_lat[0],), color=couleur, linestyle='-', linewidth=1, transform=ccrs.PlateCarree())
    ax.scatter(hull_lon, hull_lat, color='red', s=10, transform=ccrs.PlateCarree(), label='Enveloppe actuelle')

    # Déterminer le point le plus proche de la destination
    closest_point = min(enveloppe_concave, key=lambda point: distance(point, position_finale))

    # Remonter la relation parent-enfant pour construire le chemin idéal
    chemin_ideal = []
    current_point = closest_point
    while current_point is not None:
        chemin_ideal.append(current_point)
        current_point = parent_map[current_point]

    chemin_ideal.reverse()

    if chemin_ideal:
        chemin_lat, chemin_lon = zip(*chemin_ideal)
        ax.plot(chemin_lon, chemin_lat, color='black', linestyle='-', linewidth=2, label='Route', transform=ccrs.PlateCarree())
        p_r = ax.scatter(chemin_lon, chemin_lat, color='black', s=50, transform=ccrs.PlateCarree())
        p_f = ax.scatter(position_finale[1], position_finale[0], color='green', s=100, marker='o', label='Position finale')
        p_i = ax.scatter(position_initiale[1], position_initiale[0], color='red', s=100, marker='o', label='Position initiale')
    else:
        print("Chemin idéal vide : impossible de tracer la route.")

    # Ajouter une pause pour l'affichage en temps réel
    plt.legend(handles = [p_f, p_i]) # Car je veux pas afficher en légende l'enveloppe concave
    plt.pause(0.05)

def sort_points_clockwise(points):
    center_lon = np.mean([lon for lat, lon in points])
    center_lat = np.mean([lat for lat, lon in points])

    points_with_angles = [
        (lat, lon, np.arctan2(lat - center_lat, lon - center_lon)) for lat, lon in points
    ]

    sorted_points = sorted(points_with_angles, key=lambda p: p[2])

    return [(lat, lon) for lat, lon, angle in sorted_points]

def elaguer_enveloppe(points, distance):
    def calculer_distance(p1, p2):
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    points_elagues = []
    for point in points:
        trop_proche = any(calculer_distance(point, autre) < distance for autre in points_elagues)
        if not trop_proche:
            points_elagues.append(point)
    
    return points_elagues

def calculer_cap(lat1, lon1, lat2, lon2):
    # Conversion des degrés en radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    # Différence de longitude
    delta_lon = lon2 - lon1

    # Calcul du cap en radians
    x = math.sin(delta_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    cap = math.atan2(x, y)

    # Conversion en degrés et normalisation entre 0° et 360°
    cap = math.degrees(cap)
    if cap < 0:
        cap += 360

    return cap


def itere_jusqua_dans_enveloppe(position_initiale, position_finale, pas_temporel, pas_angle, tolerance, loc_nav, live=False, enregistrement=True, streamlit = False):
    
    heure = p.heure_début
    
    temp = pas_temporel
    
    positions = [position_initiale]
    
    iter_count = 0
    
    parent_map = {position_initiale: None}
    
    envconcave_precedent = []
    
    if live:
        fig, ax = plt.subplots(figsize=(20, 16), subplot_kw={'projection': ccrs.PlateCarree()})
        ax.set_extent(loc_nav, crs=ccrs.PlateCarree())
        ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1)
        ax.add_feature(cfeature.BORDERS.with_scale('10m'), linestyle=':')
        ax.add_feature(cfeature.LAND, facecolor='lightgray')
        ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
        plt.title('Itération et Enveloppe Concave')
        plt.grid(True)
        plt.legend()
        plt.tight_layout()

    while True:
        if p.print_données:    
            print(f"Iteration {iter_count}:")
            print('Heure ', heure)

        liste_parents_enfants = prochains_points_liste_parent_enfants(positions, temp, pas_angle, math.floor(heure), filtrer_par_distance=True)
        
        heure += pas_temporel
        
        points_aplatis = flatten_list_fast(liste_parents_enfants)
        
        enveloppe_concave = envconc.enveloppe_concave(np.array((points_aplatis)))
        enveloppe_concave = elaguer_enveloppe(enveloppe_concave, p.rayon_elemination)
        enveloppe_concave = [
            point for point in enveloppe_concave
            if not any(np.array_equal(point, precedent) for precedent in envconcave_precedent)
        ]
        enveloppe_concave.append((position_initiale)) 
        enveloppe_concave = sort_points_clockwise(enveloppe_concave)
        envconcave_precedent = enveloppe_concave
        
        if p.print_données:
            print("Nombre de points dans enveloppe_concave:", len(enveloppe_concave), len(points_aplatis))

        for parent, enfants in liste_parents_enfants:
            for enfant in enfants:
                if enfant not in parent_map:
                    parent_map[enfant] = parent

        
        if live:
            plot_point_live(ax, enveloppe_concave, parent_map, position_initiale, position_finale, step_index=heure, loc=loc_nav)
                
        # Mettre à jour les positions pour la prochaine itération
        positions = enveloppe_concave
        if p.print_données:
            print("le nombre de points est : ", len(positions))
        
        if dist_bateau_point(positions, position_finale, p.tolerance):
            if temp >= 0.5:
                temp *= 2/3

        closest_point = min(enveloppe_concave, key=lambda point: distance(point, position_finale))
        if p.print_données:
            print('distance arrivée, point_plus_proche ', distance(closest_point, position_finale))

        
        if dist_bateau_point(positions, position_finale, tolerance):
            print("La position finale est maintenant dans l'enveloppe concave.")
            
            # Détermination du point le plus proche de la position finale
            closest_point = min(points_aplatis, key=lambda point: distance(point, position_finale))
            print(f"Le point le plus proche de la position finale est : {closest_point}")
            
            # Tracer le chemin idéal en remontant les relations parent-enfant
            chemin_ideal = []
            current_point = closest_point
            while current_point is not None:
                chemin_ideal.append(current_point)
                current_point = parent_map[current_point]
            
            chemin_ideal.reverse()  # Inverser pour avoir le chemin de l'origine à la destination
            chemin_lat, chemin_lon = zip(*chemin_ideal)

            if p.data_route:
                with open("Informations_route.txt", "w") as fichier:
                    n = len(chemin_lon)
                    for i in range(n-1):
                        horaire = p.heure_début + i*p.pas_temporel
                        val_vent = rv.get_wind_at_position(chemin_lat[i], chemin_lon[i], horaire) 
                        fichier.write(f"Heure: {horaire}\n")
                        fichier.write(f"Position : {chemin_lat[i], chemin_lon[i]}\n")
                        cap = calculer_cap(chemin_lat[i], chemin_lon[i], chemin_lat[i+1], chemin_lon[i+1])
                        fichier.write(f"Prediction de vent a la position {val_vent[1]} degre pour {val_vent[0]} knd\n")
                        fichier.write(f"Cap : {round(cap, 2)}\n")
                        fichier.write(f"Vitesse : {round(recup_vitesse_fast(polaire(val_vent[0]), val_vent[1] - cap), 2)}\n")
                        fichier.write("-----------------------------------------------------------\n")


                    
            if not live and not streamlit:
                rv.plot_grib(heure = [heure], route={'lon': chemin_lon, 'lat': chemin_lat})

            if live:      
                plt.plot(chemin_lon, chemin_lat, color='black', linestyle='-', linewidth=2, label='Chemin Idéal')
                plt.scatter(chemin_lon, chemin_lat, color='black', s=50)
                plt.show()
                
            
            break        
        
        iter_count += 1
        stop = time()
    
    if enregistrement:
        lien_dossier = "route_ideale" 
        rv.enregistrement_route(chemin_lon, chemin_lat, pas_temporel, output_dir=lien_dossier)
    
    return {'lon': chemin_lon, 'lat': chemin_lat}

#Avant dans la fonction polaire, mais je le sors pour le calculer une fois
polaire_df = pd.read_csv(p.polaire, delimiter=p.delimeter, index_col=0)
liste_angle = polaire_df.index

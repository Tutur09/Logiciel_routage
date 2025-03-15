import numpy as np
import pandas as pd
import math
from time import time
import matplotlib.pyplot as plt
from copy import copy

from cartopy import crs as ccrs, feature as cfeature

import Routage_Vent as rv
import Routage_Paramètres as p
import Routage_Enveloppe_Concave as envconc
import Routage_Coastline as rc

from concurrent.futures import ThreadPoolExecutor

"Constantes"
R = 3440.0

def projection(position, cap, distance):
    lat_ini = position[0]    
    long_ini = position[1]
    lat_ini_rad = math.radians(lat_ini)
    long_ini_rad = math.radians(long_ini)
    
    cap_rad = math.radians(cap)
    
    distance_ratio = distance / R
    
    new_lat_rad = math.asin(math.sin(lat_ini_rad) * math.cos(distance_ratio) + 
                            math.cos(lat_ini_rad) * math.sin(distance_ratio) * math.cos(cap_rad))
    
    new_long_rad = long_ini_rad + math.atan2(math.sin(cap_rad) * math.sin(distance_ratio) * math.cos(lat_ini_rad),
                                             math.cos(distance_ratio) - math.sin(lat_ini_rad) * math.sin(new_lat_rad))
    lat_rad = math.degrees(new_lat_rad)
    lon_rad = math.degrees(new_long_rad)
    
    return (lat_rad, lon_rad)

def prochains_points(parent_point, pol_v_vent, d_vent, pas_temporel, pas_angle):
    
    liste_points = [] # Liste qui va contenir les fils du père

    angles_concervés = list(range(0, 360, pas_angle))
    for angle in angles_concervés:
        v_bateau = recup_vitesse_fast(pol_v_vent, d_vent - angle)
        liste_points.append(projection(parent_point, angle, v_bateau * pas_temporel))

    return liste_points

def traiter_point(lat, lon, point_suivant, pas_temporel, pas_angle, heure, filtrer_par_distance):
    parent_point = (lat, lon)

    v_vent, d_vent = rv.get_wind_at_position(lat, lon, heure)
    pol_v_vent = polaire(v_vent)

    enfants = prochains_points(parent_point, pol_v_vent, d_vent, pas_temporel, pas_angle)

    if filtrer_par_distance:
        # Différents filtrages en fonction des paramètres
        
        # On interdit tous les fils de sortir de la zone de navigation
        enfants = [enfant for enfant in enfants if (enfant[1] <= p.cadre_navigation[1][1] 
                                                    and enfant[1] >= p.cadre_navigation[0][1]
                                                    and enfant[0] <= p.cadre_navigation[1][0]
                                                    and enfant[0] >= p.cadre_navigation[0][0])]
        # Si le paramètre land_contact est True alors on interdit les fils qui arrivent sur la terre
        if p.land_contact:
            enfants = [enfant for enfant in enfants if rc.get_point_value(enfant) == 0]
        # Sinon on supprime les fils plus loin que le père du point final pour optimiser les calculs. Dans le cas où les contacts terrestres 
        # sont activés, ce mode ne nous interresse pas car on souhaite potentiellement faire le tour d'un bout de terre pour arriver à destination
        else:
            enfants = [enfant for enfant in enfants if plus_proche_que_parent(point_suivant, parent_point, enfant)] 
        # On retourne une liste avec le père comme premier élément et une liste de tous ss fils --> permet de déterminer plus tard le chemin idéal
    return [parent_point, enfants]

def prochains_points_liste_parent_enfants(liste, point_suivant, pas_temporel, pas_angle, heure, filtrer_par_distance=True):
    # Utilisation d’un ThreadPoolExecutor pour paralléliser les opérations --> optimisation du temps de calcul
    with ThreadPoolExecutor() as executor:
        # On lance en parallèle le traitement de chaque point de la liste
        futures = [executor.submit(traiter_point, lat, lon, point_suivant, pas_temporel, pas_angle, heure, filtrer_par_distance) 
                   for lat, lon in liste]

        # On récupère les résultats quand ils sont prêts
        liste_rendu = [f.result() for f in futures]

    return liste_rendu

def plus_proche_que_parent(point_arrivee, pos_parent, pos_enfant):
    distance_parent = math.sqrt((point_arrivee[0] - pos_parent[0])**2 + (point_arrivee[1] - pos_parent[1])**2)
    distance_enfant = math.sqrt((point_arrivee[0] - pos_enfant[0])**2 + (point_arrivee[1] - pos_enfant[1])**2)
    return distance_enfant < distance_parent

def polaire(vitesse_vent): # A partir d'un fichier polaire, on récupère que la vitesse du bateau pour une vitesse de vent vitesse_dent pour chaque angle
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

def recup_vitesse_fast(pol_v_vent, angle): # Donne la vitesse du bateau pour un angle donné
    if pol_v_vent is None:
        raise ValueError("Erreur : pol_v_vent est None, vérifiez la vitesse du vent")
    
    angle = abs(angle)
    if angle > 180:
        angle = 360 - angle

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
    print("Erreur angle")
    return None

def applatissement_liste(listes_emboitées):
    liste_applaitie = []
    pile = [listes_emboitées]

    while pile:
        lst = pile.pop()
        if isinstance(lst, list):  # Si c'est une liste, on ajoute ses éléments à la pile
            pile.extend(lst)
        elif isinstance(lst, tuple):  # Si c'est un tuple, on l'ajoute au résultat
            liste_applaitie.append(lst)
    
    return liste_applaitie

def distance_2_points(point1, point2):
    return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def dist_bateau_point(points, point_final, tolérance):
    for point in points:
        distance = distance_2_points(point, point_final)
        if distance <= tolérance:
            return True    
    return False

def midpoint_on_water(pt1, pt2):
    # Calculer le point médian
    mid = ((pt1[0] + pt2[0]) / 2, (pt1[1] + pt2[1]) / 2)
    # Vérifier si ce point est sur l'eau (get_point_value renvoie 0 pour l'eau)
    return rc.get_point_value(mid) == 0
    
def plot_points_live(ax, enveloppe_concave, parent_map, position_initiale, position_finale, route, step_index, loc, couleur='blue'):
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
    if p.land_contact:
        # Parcourir les points de l'enveloppe et tracer les segments si le point médian est sur l'eau
        for i in range(len(enveloppe_concave)):
            pt1 = enveloppe_concave[i]
            pt2 = enveloppe_concave[(i + 1) % len(enveloppe_concave)]
            if midpoint_on_water(pt1, pt2):
                ax.plot([pt1[1], pt2[1]], [pt1[0], pt2[0]], color=couleur, linestyle='-', linewidth=1, transform=ccrs.PlateCarree())
    else:
        hull_lat, hull_lon = zip(*enveloppe_concave)
        ax.plot(hull_lon, hull_lat, color=couleur, linestyle='-', linewidth=1, transform=ccrs.PlateCarree())
    
    # Affichage des points de l'enveloppe
    hull_lat, hull_lon = zip(*enveloppe_concave)
   
    if p.enveloppe:
        ax.scatter(hull_lon, hull_lat, color='red', s=10, transform=ccrs.PlateCarree(), label='Enveloppe actuelle')
    ax.scatter(hull_lon, hull_lat, color='red', s=10, transform=ccrs.PlateCarree(), label='Enveloppe actuelle')

    # Déterminer le point le plus proche de la destination
    closest_point = min(enveloppe_concave, key=lambda point: distance_2_points(point, position_finale))

    # Remonter la relation parent-enfant pour construire le chemin idéal
    chemin_ideal = []
    current_point = closest_point
    while current_point is not None:
        chemin_ideal.append(current_point)
        current_point = parent_map[current_point]

    chemin_ideal.reverse()
    
    chemin_ideal = route + chemin_ideal

    if chemin_ideal:
        chemin_lat, chemin_lon = zip(*chemin_ideal)
        ax.plot(chemin_lon, chemin_lat, color='black', linestyle='-', linewidth=2, label='Route', transform=ccrs.PlateCarree())
        p_r = ax.scatter(chemin_lon, chemin_lat, color='black', s=50, transform=ccrs.PlateCarree())
        p_f = ax.scatter(p.points[-1][1], p.points[-1][0], color='red', s=100, marker='o', label='Position finale')
        p_i = ax.scatter(p.points[0][1], p.points[0][0], color='green', s=100, marker='o', label='Position initiale')
        for point in p.points[1:-1]:
            ax.scatter(point[1], point[0], color = 'black', s= 70, marker = 'o', label = 'point intermédiare')
    else:
        print("Chemin idéal vide : impossible de tracer la route.")

    # Ajouter une pause pour l'affichage en temps réel
    plt.legend(handles = [p_f, p_i]) # Car je veux pas afficher en légende l'enveloppe concave
    plt.pause(0.05)

def plot_points_live_tk(ax, canvas, enveloppe_concave, parent_map, position_initiale, position_finale, route, step_index, loc, couleur='blue'):

    # Effacer uniquement les vecteurs de vent et les chemins, mais garder les enveloppes
    for artist in ax.collections:
        if artist.get_label() != "":#'Enveloppe actuelle':  # Ne pas supprimer l'enveloppe
            artist.remove()

    for line in ax.lines:
        if line.get_label() == 'Route':  # Supprimer le chemin idéal
            line.remove()

    rv.plot_wind_tk(ax, canvas, loc, step_indices=[step_index])

    # Vérifier que l'enveloppe est bien une liste de points valides
    if not isinstance(enveloppe_concave, list) or not all(isinstance(point, (list, tuple)) and len(point) == 2 for point in enveloppe_concave):
        print(f"L'enveloppe est invalide : {enveloppe_concave}")
        return

    # Tracer l'enveloppe concave    
    if p.land_contact:
        # Parcourir les points de l'enveloppe et tracer les segments si le point médian est sur l'eau
        for i in range(len(enveloppe_concave)):
            pt1 = enveloppe_concave[i]
            pt2 = enveloppe_concave[(i + 1) % len(enveloppe_concave)]
            if midpoint_on_water(pt1, pt2):
                ax.plot([pt1[1], pt2[1]], [pt1[0], pt2[0]], color='red', linestyle='-', linewidth=1, transform=ccrs.PlateCarree())
    else:
        hull_lat, hull_lon = zip(*enveloppe_concave)
        ax.plot(hull_lon, hull_lat, color=couleur, linestyle='-', linewidth=1, transform=ccrs.PlateCarree())
    
    # Affichage des points de l'enveloppe
    hull_lat, hull_lon = zip(*enveloppe_concave)
    
    if p.enveloppe:
        ax.plot(hull_lon, hull_lat, color=couleur, linestyle='-', linewidth=1, transform=ccrs.PlateCarree())
    ax.scatter(hull_lon, hull_lat, color='red', s=10, transform=ccrs.PlateCarree(), label='Enveloppe actuelle')

    # Déterminer le point le plus proche de la destination
    closest_point = min(enveloppe_concave, key=lambda point: distance_2_points(point, position_finale))

    # Remonter la relation parent-enfant pour construire le chemin idéal
    chemin_ideal = []
    current_point = closest_point
    while current_point is not None:
        chemin_ideal.append(current_point)
        current_point = parent_map[current_point]

    chemin_ideal.reverse()
    chemin_ideal = route + chemin_ideal

    if chemin_ideal:
        chemin_lat, chemin_lon = zip(*chemin_ideal)
        ax.plot(chemin_lon, chemin_lat, color='black', linestyle='-', linewidth=2, label='Route', transform=ccrs.PlateCarree())
        p_r = ax.scatter(chemin_lon, chemin_lat, color='black', s=50, transform=ccrs.PlateCarree())
        p_f = ax.scatter(p.points[-1][1], p.points[-1][0], color='red', s=100, marker='o', label='Position finale')
        p_i = ax.scatter(p.points[0][1], p.points[0][0], color='green', s=100, marker='o', label='Position initiale')
        for point in p.points[1:-1]:
            ax.scatter(point[1], point[0], color='black', s=70, marker='o', label='point intermédiaire')
    else:
        print("Chemin idéal vide : impossible de tracer la route.")

    # Mettre à jour l'affichage dans la fenêtre Tkinter
    plt.legend(handles=[p_f, p_i])  # Exclure l'enveloppe concave de la légende
    canvas.draw_idle()
    canvas.flush_events()

def elaguer_enveloppe(points, distance):
    def calculer_distance(p1, p2):
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    points_elagués = []
    for point in points:
        trop_proche = any(calculer_distance(point, autre) < distance for autre in points_elagués)
        if not trop_proche:
            points_elagués.append(point)
    
    return points_elagués

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

from scipy.spatial import ConvexHull


def farthest_pair(points):
    points = np.array(points)
    hull = ConvexHull(points)
    hull_points = points[hull.vertices]  # Sommets de l'enveloppe convexe

    max_dist = 0
    farthest_pair = None

    # Utilisation des "rotating calipers"
    k = 1  # Indice du point opposé sur l'enveloppe
    for i in range(len(hull_points)):
        while True:
            next_k = (k + 1) % len(hull_points)
            if distance_2_points(hull_points[i], hull_points[next_k]) > distance_2_points(hull_points[i], hull_points[k]):
                k = next_k
            else:
                break
        dist = distance_2_points(hull_points[i], hull_points[k])
        if dist > max_dist:
            max_dist = dist
            farthest_pair = (tuple(hull_points[i]), tuple(hull_points[k]))

    return farthest_pair

def itere_jusqua_dans_enveloppe(points):
    
    if p.live:
        fig, ax = plt.subplots(figsize=(20, 16), subplot_kw={'projection': ccrs.PlateCarree()})
        ax.set_extent(p.loc_nav, crs=ccrs.PlateCarree())
        ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1)
        ax.add_feature(cfeature.BORDERS.with_scale('10m'), linestyle=':')
        ax.add_feature(cfeature.LAND, facecolor='lightgray')
        ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
        plt.title('Itération et Enveloppe Concave')
        plt.grid(True)
        # plt.legend()
        plt.tight_layout()
        
    def itération(point1, point2, heure, parent_map ,points = points, route = []):
        
        positions = [point1]
        iter_count = 0
        
        while True:
            if p.print_données:  
                print(f"Iteration {iter_count}:")
                print('Heure ', heure)

            liste_parents_enfants = prochains_points_liste_parent_enfants(positions, point2, p.pas_temporel, p.pas_angle, math.floor(heure), filtrer_par_distance=True)
            heure += p.pas_temporel
            points_aplatis = applatissement_liste(liste_parents_enfants) 
                       
            enveloppe_concave = envconc.enveloppe_concave(np.array((points_aplatis)))
            if not p.land_contact:
                (p1, p2) = farthest_pair(enveloppe_concave)

                n1 = enveloppe_concave.index(p1)
                n2 = enveloppe_concave.index(p2)
                if n1 > n2:
                    n1, n2 = n2, n1
                enveloppe_concave1 = enveloppe_concave[n1:n2+1]
                enveloppe_concave2 = enveloppe_concave[n2:] + enveloppe_concave[:n1+1]
                m1 = 1/len(enveloppe_concave1) * sum(distance_2_points(enveloppe_concave1[i], point2) for i in range(len(enveloppe_concave1)))
                m2 = 1/len(enveloppe_concave2) * sum(distance_2_points(enveloppe_concave2[i], point2) for i in range(len(enveloppe_concave2)))
                
                if m1 <= m2:
                    enveloppe_concave = enveloppe_concave1
                else:
                    enveloppe_concave = enveloppe_concave2
            
            enveloppe_concave = elaguer_enveloppe(enveloppe_concave, p.rayon_elemination)
                        
            if p.print_données:
                print("Nombre de points dans enveloppe_concave:", len(enveloppe_concave), len(points_aplatis))

            for parent, enfants in liste_parents_enfants:
                for enfant in enfants:
                    if enfant not in parent_map:
                        parent_map[enfant] = parent

            
            if p.live:
                plot_points_live(ax, enveloppe_concave, parent_map, point1, point2, route, step_index=heure, loc=p.loc_nav)
                if p.enregistrement_live:
                    plot_filename = f"{"route_ideale"}/route_ideale_vent_heure_{heure}.png"
                    plt.savefig(plot_filename)
                    print(f"Plot enregistré sous : {plot_filename}")    
            # Mettre à jour les positions pour la prochaine itération
            positions = enveloppe_concave
            if p.print_données:
                print("le nombre de points est : ", len(positions))
            
            if dist_bateau_point(positions, point2, p.tolerance_arrivée):
                print(points)
                last_point = points.pop(0)
                print(points)
                print(len(points))
                
                if len(points) == 0:
                    print("La position finale est maintenant dans l'enveloppe concave.")
                    
                    # Détermination du point le plus proche de la position finale
                    closest_point = min(points_aplatis, key=lambda point: distance_2_points(point, last_point))
                    print(f"Le point le plus proche de la position finale est : {closest_point}")
                    
                    # Tracer le chemin idéal en remontant les relations parent-enfant
                    chemin_ideal = []
                    current_point = closest_point
                    while current_point is not None:
                        chemin_ideal.append(current_point)
                        current_point = parent_map[current_point]
                    
                    chemin_ideal.reverse()  # Inverser pour avoir le chemin de l'origine à la destination
                    chemin_ideal = route + chemin_ideal
                    if chemin_ideal:
                        chemin_lat, chemin_lon = zip(*chemin_ideal)
                    else:
                        print("⚠️ Aucun chemin trouvé, retour d'une liste vide.")
                        chemin_lat, chemin_lon = [], []

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
                            
                    if not p.live: #and not p.streamlit:
                        rv.plot_grib(heure = [heure], route={'lon': chemin_lon, 'lat': chemin_lat})

                    if p.live:      
                    #     plt.plot(chemin_lon, chemin_lat, color="black", linestyle='-', linewidth=2, label='Chemin Idéal')
                    #     plt.scatter(chemin_lon, chemin_lat, color='black', s=50)
                        plt.show()
                    break

                else:
                    if points:
                        closest_point = min(points_aplatis, key=lambda point: distance_2_points(point, last_point))
                        print(f"Le point le plus proche de la position intermédiaire est : {closest_point}")
                        
                        # Tracer le chemin idéal en remontant les relations parent-enfant
                        chemin_ideal = []
                        current_point = closest_point
                        while current_point is not None:
                            chemin_ideal.append(current_point)
                            current_point = parent_map[current_point]
                        
                        chemin_ideal.reverse()
                        route = route + chemin_ideal
                        iter_count += 1
                        itération(closest_point, points[0], heure, {closest_point: None}, copy(points), route)
                    else:
                        print("🎯 Destination atteinte. Fin du routage.")
                    
                break
        if p.enregistrement:
            lien_dossier = "route_ideale" 
            rv.enregistrement_route(chemin_lon, chemin_lat, p.pas_temporel, output_dir=lien_dossier)
        
        return {'lon': chemin_lon, 'lat': chemin_lat}
    
    point_départ = points.pop(0)
    point_suivant = points[0]
    dict_chemin = itération(point_départ, point_suivant, p.heure_début, {point_départ: None}, points, route = [])
    return dict_chemin

def itere_jusqua_dans_enveloppe_tk(points, ax, canvas):
    """Effectue le routage et affiche en temps réel dans la fenêtre Tkinter"""
    
    def itération(point1, point2, heure, parent_map, points=points, route=[]):
        
        positions = [point1]
        iter_count = 0
        
        while True:
            if p.print_données:  
                print(f"Iteration {iter_count}:")
                print('Heure ', heure)

            liste_parents_enfants = prochains_points_liste_parent_enfants(positions, point2, p.pas_temporel, p.pas_angle, math.floor(heure), filtrer_par_distance=True)
            heure += p.pas_temporel
            points_aplatis = applatissement_liste(liste_parents_enfants)
            
            enveloppe_concave = envconc.enveloppe_concave(np.array((points_aplatis)))
            if not p.land_contact:
                (p1, p2) = farthest_pair(enveloppe_concave)

                n1 = enveloppe_concave.index(p1)
                n2 = enveloppe_concave.index(p2)
                if n1 > n2:
                    n1, n2 = n2, n1
                enveloppe_concave1 = enveloppe_concave[n1:n2+1]
                enveloppe_concave2 = enveloppe_concave[n2:] + enveloppe_concave[:n1+1]
                m1 = 1/len(enveloppe_concave1) * sum(distance_2_points(enveloppe_concave1[i], point2) for i in range(len(enveloppe_concave1)))
                m2 = 1/len(enveloppe_concave2) * sum(distance_2_points(enveloppe_concave2[i], point2) for i in range(len(enveloppe_concave2)))
                
                if m1 <= m2:
                    enveloppe_concave = enveloppe_concave1
                else:
                    enveloppe_concave = enveloppe_concave2
            
            enveloppe_concave = elaguer_enveloppe(enveloppe_concave, p.rayon_elemination)
            
            if p.print_données:
                print("Nombre de points dans enveloppe_concave:", len(enveloppe_concave), len(points_aplatis))

            for parent, enfants in liste_parents_enfants:
                for enfant in enfants:
                    if enfant not in parent_map:
                        parent_map[enfant] = parent
            
            # Mise à jour en temps réel avec Tkinter
            plot_points_live_tk(ax, canvas, enveloppe_concave, parent_map, point1, point2, route, step_index=heure, loc=p.loc_nav)

            positions = enveloppe_concave
            if p.print_données:
                print("le nombre de points est : ", len(positions))
            
            if dist_bateau_point(positions, point2, p.tolerance_arrivée):
                last_point = points.pop(0)

                if len(points) == 0:
                    print("La position finale est maintenant dans l'enveloppe concave.")
                    
                    closest_point = min(points_aplatis, key=lambda point: distance_2_points(point, last_point))
                    print(f"Le point le plus proche de la position finale est : {closest_point}")
                    
                    chemin_ideal = []
                    current_point = closest_point
                    while current_point is not None:
                        chemin_ideal.append(current_point)
                        current_point = parent_map[current_point]
                    
                    chemin_ideal.reverse()
                    chemin_ideal = route + chemin_ideal
                    chemin_lat, chemin_lon = zip(*chemin_ideal)

                    if p.data_route:
                        with open("Informations_route.txt", "w") as fichier:
                            for i in range(len(chemin_lon) - 1):
                                horaire = p.heure_début + i * p.pas_temporel
                                val_vent = rv.get_wind_at_position(chemin_lat[i], chemin_lon[i], horaire) 
                                fichier.write(f"Heure: {horaire}\n")
                                fichier.write(f"Position : {chemin_lat[i], chemin_lon[i]}\n")
                                cap = calculer_cap(chemin_lat[i], chemin_lon[i], chemin_lat[i+1], chemin_lon[i+1])
                                fichier.write(f"Prediction de vent à {val_vent[1]}° pour {val_vent[0]} knd\n")
                                fichier.write(f"Cap : {round(cap, 2)}\n")
                                fichier.write(f"Vitesse : {round(recup_vitesse_fast(polaire(val_vent[0]), val_vent[1] - cap), 2)}\n")
                                fichier.write("-----------------------------------------------------------\n")
                            
                    if p.live:
                        canvas.draw_idle()  # 🔥 Met à jour l'affichage dans Tkinter
                    break

                else:
                    closest_point = min(points_aplatis, key=lambda point: distance_2_points(point, last_point))
                    itération(closest_point, points[0], heure, {closest_point: None}, copy(points), route)   
                break
        
        return {'lon': chemin_lon, 'lat': chemin_lat}
    
    point_départ = points.pop(0)
    point_suivant = points[0]
    dict_chemin = itération(point_départ, point_suivant, p.heure_début, {point_départ: None}, points, route=[])
    return dict_chemin


#Avant dans la fonction polaire, mais je le sors pour le calculer une fois
polaire_df = pd.read_csv(p.polaire, delimiter=p.delimeter, index_col=0)
liste_angle = polaire_df.index

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from cartopy import crs as ccrs, feature as cfeature
from matplotlib.animation import FuncAnimation
from scipy.interpolate import griddata
import cartopy.crs as ccrs
import math

file_path = r'Logiciel\QUIBERON_558'

def parse_coord(coord_str):
    position_point = coord_str.index(".")
    sign = 1
    if coord_str[0] == "-":
        sign = -1
        if position_point % 2 == 1:
            degrees = coord_str[1:3]
            minutes = coord_str[3::]
        else:
            degrees = coord_str[1:2]
            minutes = coord_str[2::]
    else:
        if position_point % 2 == 1:
            degrees = coord_str[0:1]
            minutes = coord_str[1::]
        else:
            degrees = coord_str[0:2]
            minutes = coord_str[2::]
            
    return sign * (float(degrees) + float(minutes)/60)

def ouverture_fichier_courant(file_path):
        
    blocks = []

    with open(file_path, "r", encoding="utf-8") as f:
        # Lire toutes les lignes et supprimer les sauts de ligne
        lines = [line for line in f]

    # On suppose que la première ligne est l'en-tête
    header = lines[0]
    print("Port de référence : ", header)

    # Les données commencent à la ligne 1 (index 1)
    i = 1
    while i < len(lines):
        # Vérifier qu'il reste au moins trois lignes
        if i + 2 >= len(lines):
            break
        coord_line = lines[i]
        line1 = lines[i+1]
        line2 = lines[i+2]
        i += 3

        try:
            coords = [float(parse_coord(x)) for x in coord_line.split()]
        except ValueError:
            # Si la ligne ne contient pas de nombres, on peut la sauter
            continue

        # Traitement des lignes de chiffres :
        def parse_line(line):
            # On filtre les tokens convertibles en float et on ignore les autres (par ex. "*")
            values = []

            for i in range(13):
                values += [(int(line[i*3:i*3+3]), int(line[(i*3+41):(i*3+40+4)]))]
            return values


        vive_eau = parse_line(line1)
        morte_eau = parse_line(line2)

        blocks.append({
            "coords": coords,
            "vive_eau": vive_eau,
            "morte_eau": morte_eau
            })
        
    return blocks

def plot_courant(ax, blocks, scale=1):
    import numpy as np
    from scipy.interpolate import griddata
    from cartopy import crs as ccrs
    import matplotlib.pyplot as plt

    # Extraction des données
    lats = []
    lons = []
    speed = []
    heure = 0

    for b in blocks:
        lat, lon = b["coords"]
        u, v = b["vive_eau"][heure]
        lats.append(lat)
        lons.append(lon)
        speed.append(np.sqrt(u**2 + v**2))

    lats = np.array(lats)
    lons = np.array(lons)
    speed = np.array(speed)

    # Définir une grille régulière
    grid_lon, grid_lat = np.meshgrid(
        np.linspace(min(lons), max(lons), 100),
        np.linspace(min(lats), max(lats), 100)
    )

    # Interpoler les vitesses sur la grille
    grid_speed = griddata(
        points=(lons, lats),
        values=speed,
        xi=(grid_lon, grid_lat),
        method='cubic'  # ou 'linear' pour plus robuste, 'nearest' pour brut
    )

    # Affichage du champ de vitesse comme un relief coloré
    cf = ax.contourf(
        grid_lon, grid_lat, grid_speed,
        levels=50, cmap='viridis',
        transform=ccrs.PlateCarree()
    )

    # Ajouter la colorbar
    plt.colorbar(cf, ax=ax, orientation='vertical', label='Vitesse du courant (nœuds ?)')

    return ax

def animate_courant(blocks):
    fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()}, figsize=(10, 6))

    # Préparer les grilles une seule fois
    lats = [b["coords"][0] for b in blocks]
    lons = [b["coords"][1] for b in blocks]

    grid_lon, grid_lat = np.meshgrid(
        np.linspace(min(lons), max(lons), 100),
        np.linspace(min(lats), max(lats), 100)
    )

    # Créer un objet de contourf vide, qu'on va mettre à jour
    cf = [None]  # liste pour stocker le contourf, modifiable dans update

    def update(hour):
        ax.clear()
        ax.set_title(f'Heure {hour} de la marée')
        ax.coastlines()

        u_list = []
        v_list = []
        speed = []

        for b in blocks:
            u, v = b["vive_eau"][hour]
            u_list.append(u)
            v_list.append(v)
            speed.append(np.sqrt(u**2 + v**2))

        u_list = np.array(u_list)
        v_list = np.array(v_list)
        speed = np.array(speed)
        
        
        # Normalisation des vecteurs (u, v)
        norm = np.sqrt(u_list**2 + v_list**2)
        # Éviter la division par 0
        norm[norm == 0] = 1

        u_norm = u_list / norm
        v_norm = v_list / norm
        
        # Interpolation pour affichage "relief"
        grid_speed = griddata(
            points=(lons, lats),
            values=speed,
            xi=(grid_lon, grid_lat),
            method='cubic'
        )

        # Champ de vitesse en couleur (relief)
        ax.contourf(
            grid_lon, grid_lat, grid_speed,
            levels=50, cmap='viridis',
            transform=ccrs.PlateCarree()
        )

        # Ajout des flèches pour chaque point
        ax.quiver(
            lons, lats, u_norm, v_norm,
            transform=ccrs.PlateCarree(),
            scale=100,      # plus grand = flèches plus petites
            width=0.003,   # épaisseur des flèches
            color='black',
            zorder=4
        )

        return []

    anim = FuncAnimation(fig, update, frames=12, interval=800, blit=False)

    plt.show()
    return anim

def récupérer_courant(pos, heure, blocks, type_maree="vive_eau"):
    """
    Renvoie le courant (u, v) à la position connue la plus proche de pos, interpolé temporellement.
    
    pos : (lat, lon)
    heure : datetime
    blocks : issus de ouverture_fichier_courant
    pleine_mer : datetime de la pleine mer de référence
    type_maree : "vive_eau" ou "morte_eau"
    """
    lat, lon = pos
    
    # 1. Heure relative autour de la pleine mer (entre -6h et +6h)
    heure_relative = heure

    if not (-6 <= heure_relative <= 6):
        raise ValueError("Heure hors de l'intervalle +/-6h autour de la pleine mer")

    # 2. Convertir en indices horaires (0 à 12)
    h_inf = int(np.floor(heure_relative)) + 6
    h_sup = min(h_inf + 1, 12)
    alpha = heure_relative - np.floor(heure_relative)

    # 3. Trouver le bloc spatialement le plus proche
    def distance_squared(lat1, lon1, lat2, lon2):
        return (lat1 - lat2)**2 + (lon1 - lon2)**2

    bloc_proche = min(blocks, key=lambda b: distance_squared(lat, lon, b["coords"][0], b["coords"][1]))
    print(bloc_proche)
    data = bloc_proche[type_maree]

    u1, v1 = data[h_inf]
    u2, v2 = data[h_sup]

    # 4. Interpolation temporelle linéaire
    u = (1 - alpha) * u1 + alpha * u2
    v = (1 - alpha) * v1 + alpha * v2

    return u / 10.0, v / 10.0  # Retour en nœuds

def position_courant(pos, u_courant, v_courant, pas_temporel):
    """
    Calcule la nouvelle position après déplacement dû au courant.

    pos : (lat, lon) en degrés
    u_courant, v_courant : composantes du courant en nœuds (Est, Nord)
    pas_temporel : en secondes

    Retour : (lat_new, lon_new)
    """
    lat, lon = pos

    # Conversion du courant en m/s
    u_ms = u_courant * 0.5144
    v_ms = v_courant * 0.5144

    # Distance parcourue
    dx = u_ms * pas_temporel  # en mètres (est-ouest)
    dy = v_ms * pas_temporel  # en mètres (nord-sud)

    # Approximation : 1° de lat = ~111.32 km
    delta_lat = dy / 111_320  # en degrés
    delta_lon = dx / (111_320 * math.cos(math.radians(lat)))  # en degrés

    lat_new = lat + delta_lat
    lon_new = lon + delta_lon

    return lat_new, lon_new

def vérification_position_courant(
    pos_depart,
    heure_depart,
    durée_heures,
    blocks,
    type_maree="vive_eau",
    pas_h=1
    ):
    """
    Affiche la dérive d'un point sous l'effet du courant, heure par heure, avec fond de carte.

    pos_depart : (lat, lon)
    heure_depart : datetime
    durée_heures : durée de la simulation (en heures)
    blocks : issus de ouverture_fichier_courant
    type_maree : "vive_eau" ou "morte_eau"
    pas_h : pas de temps en heures
    """
    pos = pos_depart
    heure = heure_depart

    lats = [pos[0]]
    lons = [pos[1]]
    heures = [heure]

    # Préparer la figure avec projection Cartopy
    fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()}, figsize=(10, 6))

    # Déterminer les bornes de carte à partir des blocs
    bloc_lats = [b["coords"][0] for b in blocks]
    bloc_lons = [b["coords"][1] for b in blocks]

    lat_min, lat_max = min(bloc_lats) - 0.1, max(bloc_lats) + 0.1
    lon_min, lon_max = min(bloc_lons) - 0.1, max(bloc_lons) + 0.1

    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())
    ax.coastlines(resolution='10m')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels = gl.right_labels = False

    for t in range(0, durée_heures, pas_h):
        try:
            u, v = récupérer_courant(pos, heure, blocks, type_maree=type_maree)

        except Exception as e:
            print(f"Erreur à t={t}h : {e}")
            break

        # Avancer dans le temps
        pos = position_courant(pos, u, v, pas_h)
        
        if heure < 6:
            heure += pas_h
        else:
            heure = -6

        lats.append(pos[0])
        lons.append(pos[1])
        heures.append(heure)

        # Mise à jour du tracé
        ax.clear()
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())
        ax.coastlines(resolution='10m')
        ax.add_feature(cfeature.LAND, facecolor='lightgray')
        ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
        ax.add_feature(cfeature.BORDERS, linestyle=':')
        gl = ax.gridlines(draw_labels=True)
        gl.top_labels = gl.right_labels = False

        ax.plot(lons, lats, marker='o', linestyle='-', color='blue', transform=ccrs.PlateCarree())

        plt.pause(0.3)

    plt.show()

blocks = ouverture_fichier_courant(file_path)

if __name__ == "__main__":
    # animate_courant(blocks)
    # print(récupérer_courant((47.4, -3), 0, blocks))
    vérification_position_courant(
        pos_depart=(47.4, -3.05),
        heure_depart=0,
        durée_heures=100,
        blocks=blocks,
        type_maree="vive_eau"
    )
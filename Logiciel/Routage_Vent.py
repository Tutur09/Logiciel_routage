#Je sépare la partie vent du code afin de rendre le code plus compréhensible
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
import os
import Routage_Paramètres as p
from cartopy import crs as ccrs, feature as cfeature
import xarray as xr
import pickle




def excel_to_uv_components2(excel_file):
    # Lire le fichier Excel
    data = pd.read_excel(excel_file, header=None)
    
    # Lire les paramètres initiaux
    lat_i, lon_i, grid_size = data.iloc[1, 0], data.iloc[1, 1], data.iloc[1, 2]
    nb_col, nb_lig = data.shape[1] - 1, data.shape[0] - 4
    
    # Déterminer les limites de latitude et longitude
    lat_max = lat_i - grid_size * nb_lig
    lon_max = lon_i + grid_size * nb_col

    # Construire les grilles de latitudes et longitudes
    latitudes = np.linspace(lat_i, lat_max, nb_lig)
    longitudes = np.linspace(lon_i, lon_max, nb_col)

    # Extraire les données u et v
    u_values = []
    v_values = []
    for i in range(nb_lig):
        u_row = []
        v_row = []
        for j in range(nb_col):
            u_v = data.iloc[4 + nb_lig - 1 - i, j + 1].split(';')
            u_row.append(float(u_v[0]))  # Composante u
            v_row.append(float(u_v[1]))  # Composante v
        u_values.append(u_row)
        v_values.append(v_row)

    # Convertir en numpy arrays
    u_values = np.array(u_values)
    v_values = np.array(v_values)

    # Ajouter une dimension temporelle pour simuler des données GRIB
    u = u_values[np.newaxis, :, :]  # Shape: [1, latitude, longitude]
    v = v_values[np.newaxis, :, :]  # Shape: [1, latitude, longitude]

    return u, v, latitudes, longitudes

def excel_to_uv_components(excel_file):
    # Lecture du fichier Excel, en considérant la première ligne comme en-têtes de colonnes
    # et la première colonne (lat\lon, 65, 64, etc.) comme index.
    df = pd.read_excel(excel_file, header=0, index_col=0)
    
    # À présent, df.index contient les latitudes et df.columns contient les longitudes.
    # Convertir ces valeurs en type float (elles devraient déjà être numériques, sinon forcées)
    latitudes = df.index.astype(float).values
    longitudes = df.columns.astype(float).values

    # Chaque cellule contient une chaîne du type "U;V"
    # On va les convertir en tuples (u, v).
    def parse_uv(cell):
        # Séparer sur le point-virgule
        u_str, v_str = cell.split(';')
        # Remplacer la virgule par un point si nécessaire et convertir en float
        u_val = float(u_str.replace(',', '.'))
        v_val = float(v_str.replace(',', '.'))
        return (u_val, v_val)

    # Appliquer ce parsing à chaque cellule
    uv_values = df.applymap(parse_uv)

    # Extraire les composantes u et v dans deux tableaux distincts
    u_values = uv_values.applymap(lambda x: x[0]).values
    v_values = uv_values.applymap(lambda x: x[1]).values

    # Ajouter une dimension temporelle (simule un pas de temps unique) pour rester cohérent avec le format "GRIB"
    u = u_values[np.newaxis, :, :]  # Shape: (1, nombre_de_latitudes, nombre_de_longitudes)
    v = v_values[np.newaxis, :, :]

    return u, v, latitudes, longitudes

def plot_wind(ax, loc, step_indices=[1], chemin_x=None, chemin_y=None):
    ax.set_extent(loc, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1)
    ax.add_feature(cfeature.BORDERS.with_scale('10m'), linestyle=':')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
    ax.scatter(p.position_finale[0], p.position_finale[1], color='black', s=100, marker='*', label='Position Finale')

    # Définir les plages de vitesse du vent et les couleurs associées
    cmap = mcolors.ListedColormap(p.colors_windy)
    norm = mcolors.BoundaryNorm(p.wind_speed_bins, cmap.N)

    for step_index in step_indices:
        if p.type == "grib":
            try:
                # GRIB : Extraire les données pour l'étape spécifiée
                u10_specific = ds['u10'].isel(step=int(step_index)).values
                v10_specific = ds['v10'].isel(step=int(step_index)).values
                latitudes = ds['latitude'].values
                longitudes = ds['longitude'].values
            except Exception as e:
                u10_specific = ds['u10'].isel(step=int(-1)).values
                v10_specific = ds['v10'].isel(step=int(-1)).values
                latitudes = ds['latitude'].values
                longitudes = ds['longitude'].values

        elif p.type == "excel":
            # Excel : Les données ne changent pas selon l'étape (pas de temps)
            u10_specific = u_xl[0]
            v10_specific = v_xl[0]
            latitudes = lat_xl
            longitudes = lon_xl

        else:
            raise ValueError("La source spécifiée doit être 'grib' ou 'excel'.")

        # Sous-échantillonnage
        latitudes = latitudes[::p.skip]
        longitudes = longitudes[::p.skip]
        u10_specific = u10_specific[::p.skip, ::p.skip]
        v10_specific = v10_specific[::p.skip, ::p.skip]

        # Calcul de la vitesse du vent
        wind_speed = 1.852 * np.sqrt(u10_specific**2 + v10_specific**2)

        # Colorier la carte avec les vitesses du vent
        mesh = ax.pcolormesh(
            longitudes, latitudes, wind_speed,
            transform=ccrs.PlateCarree(), cmap=cmap, norm=norm, shading='auto'
        )

        # Ajouter des vecteurs noirs pour la direction
        ax.barbs(
            longitudes[::p.skip_vect_vent], latitudes[::p.skip_vect_vent],
            1.852 * u10_specific[::p.skip_vect_vent, ::p.skip_vect_vent], 1.852 * v10_specific[::p.skip_vect_vent, ::p.skip_vect_vent],
            length=5, pivot='middle', barbcolor='black', linewidth=0.6, 
            transform=ccrs.PlateCarree()
        )

        # Ajouter une barre de couleur pour l'intensité
        if p.drapeau:
            cbar = plt.colorbar(
                mappable=mesh, ax=ax, orientation='vertical', pad=0.02, shrink=0.5
            )
            cbar.set_label("Vitesse du vent (nœuds)")
        p.drapeau = False

        # Tracer le chemin idéal s'il est fourni
        if chemin_x is not None and chemin_y is not None:
            ax.plot(chemin_x, chemin_y, color='black', linestyle='-', linewidth=2, label='Chemin Idéal', transform=ccrs.PlateCarree())
            ax.scatter(chemin_x, chemin_y, color='black', s=50, transform=ccrs.PlateCarree())
        
def plot_wind_tk(ax, canvas, loc, step_indices=[1], chemin_x=None, chemin_y=None, couleur = False):
    # ax.set_extent(loc, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE.with_scale("10m"), linewidth=1)
    ax.add_feature(cfeature.BORDERS.with_scale("10m"), linestyle=":")
    ax.add_feature(cfeature.LAND, facecolor="lightgray")
    ax.add_feature(cfeature.OCEAN, facecolor="lightblue")
    ax.scatter(p.position_finale[0], p.position_finale[1], color='black', s=100, marker='*', label='Position Finale')

    # Définition de la colormap pour la vitesse du vent
    cmap = mcolors.ListedColormap(p.colors_windy)
    norm = mcolors.BoundaryNorm(p.wind_speed_bins, cmap.N)

    for step_index in step_indices:
        try:
            if p.type == "grib":
                # Extraction des données GRIB
                u10_specific = ds['u10'].isel(step=int(step_index)).values
                v10_specific = ds['v10'].isel(step=int(step_index)).values
                latitudes = ds['latitude'].values
                longitudes = ds['longitude'].values

            elif p.type == "excel":
                # Extraction des données Excel
                u10_specific = u_xl[0]
                v10_specific = v_xl[0]
                latitudes = lat_xl
                longitudes = lon_xl

            else:
                raise ValueError("La source de données doit être 'grib' ou 'excel'.")

            # Sous-échantillonnage
            skip = p.skip
            latitudes = latitudes[::skip]
            longitudes = longitudes[::skip]
            u10_specific = u10_specific[::skip, ::skip]
            v10_specific = v10_specific[::skip, ::skip]

            # Calcul de la vitesse du vent
            wind_speed = 1.852 * np.sqrt(u10_specific**2 + v10_specific**2)

            # Colorier la carte avec les vitesses du vent
            if couleur:
                mesh = ax.pcolormesh(
                    longitudes, latitudes, wind_speed,
                    transform=ccrs.PlateCarree(), cmap=cmap, norm=norm, shading='auto'
                )

            # Ajouter des vecteurs noirs pour la direction du vent
            skip_vect = p.skip_vect_vent
            ax.barbs(
                longitudes[::skip_vect], latitudes[::skip_vect],
                1.852 * u10_specific[::skip_vect, ::skip_vect],
                1.852 * v10_specific[::skip_vect, ::skip_vect],
                length=5, pivot='middle', barbcolor='black', linewidth=0.6,
                transform=ccrs.PlateCarree()
            )

            # if p.drapeau:
            #     cbar = plt.colorbar(
            #         mappable=mesh, ax=ax, orientation='vertical', pad=0.02, shrink=0.5
            #     )
            #     cbar.set_label("Vitesse du vent (nœuds)")
            # p.drapeau = False

            # Tracer le chemin idéal s'il est fourni
            if chemin_x is not None and chemin_y is not None:
                ax.plot(chemin_x, chemin_y, color='black', linestyle='-', linewidth=2, label='Chemin Idéal', transform=ccrs.PlateCarree())
                ax.scatter(chemin_x, chemin_y, color='black', s=50, transform=ccrs.PlateCarree())

        except IndexError:
            print(f"⚠️ Avertissement : step_index {step_index} hors limite des données.")

    # Mettre à jour l'affichage en live dans Tkinter
    canvas.draw()

def plot_grib(heure, position=None, route=None, context=None, skip = p.skip, skip_vect_vent = p.skip_vect_vent, loc_nav = p.loc_nav):
    if not isinstance(heure, list):
        heure = [heure]

    num_plots = len(heure)
    nrows = int(np.ceil(np.sqrt(num_plots)))
    ncols = int(np.ceil(num_plots / nrows))

    fig, axes = plt.subplots(
        nrows, ncols, figsize=(20, 16), 
        subplot_kw={'projection': ccrs.PlateCarree()}
    )
    
    # Flatten axes to ensure consistent iteration
    axes = np.array(axes).flatten() if num_plots > 1 else [axes]

    manager = plt.get_current_fig_manager()
    try:
        manager.window.wm_geometry("+100+100")
    except AttributeError:
        manager.window.setGeometry(100, 100, 800, 600)

    for idx, (ax, h) in enumerate(zip(axes, heure)):
        # Set map extent and features
        if hasattr(ax, 'set_extent'):  # Ensure ax is a valid axis with set_extent
            ax.set_extent(loc_nav, crs=ccrs.PlateCarree())
            ax.coastlines()
            ax.add_feature(cfeature.BORDERS.with_scale('10m'), linestyle=':')
            ax.add_feature(cfeature.LAND, facecolor='lightgray')
            ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
            ax.grid(True)

            # Wind speed colormap
            cmap = mcolors.ListedColormap(p.colors_windy)
            norm = mcolors.BoundaryNorm(p.wind_speed_bins, cmap.N)

            # Extract wind data for the specific hour
            if p.type == "grib":
                try:
                    u10_specific = ds['u10'].isel(step=int(h)).values
                    v10_specific = ds['v10'].isel(step=int(h)).values
                    latitudes = ds['latitude'].values
                    longitudes = ds['longitude'].values
                except Exception as e:
                    print(f"Error accessing GRIB data: {e}")
                    continue
            elif p.type == "excel":
                u10_specific = u_xl[0]
                v10_specific = v_xl[0]
                latitudes = lat_xl
                longitudes = lon_xl
            else:
                raise ValueError("Source de données invalide.")

            wind_speed = 1.852 * np.sqrt(u10_specific[::skip, ::skip]**2 + v10_specific[::skip, ::skip]**2)

            # Plot wind speed
            mesh = ax.pcolormesh(
                longitudes[::skip], latitudes[::skip], wind_speed,
                transform=ccrs.PlateCarree(), cmap=cmap, norm=norm, shading='auto'
            )

            # Pour ajout des barbes
            
            ax.barbs(
                longitudes[::skip_vect_vent], latitudes[::skip_vect_vent],
                1.852 * u10_specific[::skip_vect_vent, ::skip_vect_vent],
                1.852 * v10_specific[::skip_vect_vent, ::skip_vect_vent],
                length=5, pivot='middle', barbcolor='black', linewidth=0.6,
                transform=ccrs.PlateCarree()
            )

            cbar = plt.colorbar(mesh, ax=ax, orientation='vertical', pad=0.02, shrink=0.5)
            cbar.set_label("Vitesse du vent (nœuds)")

            # ajout de la route
            if context == "enregistrement" and route:
                ax.plot(route['lon'], route['lat'], color='black', linestyle='-', linewidth=2, transform=ccrs.PlateCarree())
                ax.scatter(route['lon'], route['lat'], color='black', s=10, transform=ccrs.PlateCarree(), label='Route')
            if context != "enregistrement" and route:
                ax.plot(route['lon'], route['lat'], color='black', linestyle='-', linewidth=2, transform=ccrs.PlateCarree())
                ax.scatter(route['lon'], route['lat'], color='black', s=10, transform=ccrs.PlateCarree(), label='Route')

            if position:
                lat, lon = position
                ax.scatter(
                    lon, lat, color='red', s=100, transform=ccrs.PlateCarree(), label="Position actuelle"
                )
                ax.legend(loc="upper right")

            ax.set_title(f"Carte des vents - Heure {h}")  # - p.heure_début
        else:
            print(f"Invalid axis at index {idx}")

    if context is None:
        plt.show()

def get_wind_at_position(lat, lon, time_step=0):
    try:
            
        lon = lon % 360 

        if p.type == 'grib':
            # Sélection des données temporelles
            u_time_step = u10_values[time_step]
            v_time_step = v10_values[time_step]
            latitudes = ds.latitude.values
            longitudes = ds.longitude.values

        elif p.type == 'excel':
            u_time_step = u_xl[0]
            v_time_step = v_xl[0]
            latitudes = lat_xl
            longitudes = lon_xl

        else:
            raise ValueError("La source spécifiée doit être 'grib' ou 'excel'.")

        # Calcul des distances
        lat_diff = np.abs(latitudes - lat)
        lon_diff = np.abs(longitudes - lon)

        if lat_diff.ndim == 1 and lon_diff.ndim == 1:  # Coordonnées 1D
            distances = lat_diff[:, None]**2 + lon_diff**2
        else:  # Coordonnées 2D
            distances = lat_diff**2 + lon_diff**2

        # Trouver l'index du point le plus proche
        closest_index = np.unravel_index(np.argmin(distances), distances.shape)

        # Récupérer les valeurs de vent
        u = u_time_step[closest_index]
        v = v_time_step[closest_index]

        # Calcul de la vitesse et de l'angle
        v_vent = 1.852 * np.sqrt(u**2 + v**2)
        a_vent = (np.degrees(np.arctan2(-u, -v))) % 360

        return v_vent, a_vent
        
    except Exception as e:
        return get_wind_at_position(lat, lon, -1)
    
def enregistrement_route(chemin_lon, chemin_lat, pas_temporel, output_dir='./'):
    # Créer le répertoire de sortie s'il n'existe pas
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    point = 0
    heure = 0

    for _ in range(0, len(chemin_lon)):
        # Définir la position actuelle
        position_actuelle = (chemin_lat[point], chemin_lon[point])

        plot_grib(
            heure=[heure],
            position=position_actuelle,
            route={
                'lon': chemin_lon[:point + 1],
                'lat': chemin_lat[:point + 1]
            },
            context = "enregistrement", skip = 10, skip_vect_vent = 10
        )

        # Sauvegarder la figure dans le répertoire de sortie
        plot_filename = f"{output_dir}/route_ideale_vent_heure_{heure}.png"
        plt.savefig(plot_filename)
        print(f"Plot enregistré sous : {plot_filename}")

        plt.close()
        heure += pas_temporel
        point += 1

def point_ini_fin(loc):
    points = [] 

    def on_click(event):
        if event.inaxes:
            x, y = float(event.xdata), float(event.ydata)
            points.append((y, x))  # Latitude, Longitude
            print(f"Point sélectionné : {y:.2f}N, {x:.2f}E")

            # Ajout d'un point rouge pour le départ, bleu pour l'arrivée, vert pour les intermédiaires
            color = "green" if len(points) == 1 else "red" if len(points) == 2 else "black"
            label = (
                "Départ" if len(points) == 1 else
                "Arrivée" if len(points) == 2 else
                f"Intermédiaire {len(points) - 2}"
            )
            ax.scatter(x, y, color=color, marker="x", s=100, zorder=5, transform=ccrs.PlateCarree(), label=label)
            ax.legend(loc="upper left")
            plt.draw()

    fig, ax = plt.subplots(figsize=(12, 7), subplot_kw={"projection": ccrs.PlateCarree()})
    
    # Définir l'étendue de la carte
    ax.set_extent(loc, crs=ccrs.PlateCarree())
    
    # Ajouter les caractéristiques géographiques
    ax.add_feature(cfeature.COASTLINE.with_scale("10m"), linewidth=1)
    ax.add_feature(cfeature.BORDERS.with_scale("10m"), linestyle=":")
    ax.add_feature(cfeature.LAND, facecolor="lightgray")
    ax.add_feature(cfeature.OCEAN, facecolor="lightblue")
    
    # Ajouter une grille de latitude/longitude
    gl = ax.gridlines(draw_labels=True, color="gray", alpha=0.5, linestyle="--")
    gl.top_labels = False
    gl.right_labels = False

    # Connecter l'événement de clic
    cid = fig.canvas.mpl_connect("button_press_event", on_click)
    
    plt.title("Cliquez pour choisir le point de départ, d'arrivée et des points intermédiaires")
    plt.show()
    
    # Retourner tous les points sélectionnés
    if len(points) >= 2:
        point_final = points.pop(1)
        points.append(point_final)
        return points
    else:
        print("Sélection incomplète. Veuillez sélectionner au moins deux points (départ et arrivée).")
        return None

  

#Chemin d'accès du fichier GRIB vent et courant (pas encore fait)
file_path = p.vent

if p.type == 'grib':
    ds = xr.open_dataset(file_path, engine='cfgrib')
    p.nb_step = ds.sizes["step"]
    if p.new:
        u10_values = [ds.u10.isel(step=int(step)).values for step in range(ds.dims['step'])]
        v10_values = [ds.v10.isel(step=int(step)).values for step in range(ds.dims['step'])]

        # Sauvegarder les variables sous forme de fichiers Pickle
        with open("u10_values.pkl", "wb") as f:
            pickle.dump(u10_values, f)
        with open("v10_values.pkl", "wb") as f:
            pickle.dump(v10_values, f)
        
    else:        
        with open("u10_values.pkl", "rb") as f:
            u10_values = pickle.load(f)
        with open("v10_values.pkl", "rb") as f:
            v10_values = pickle.load(f)
            

else:
    u_xl, v_xl, lat_xl, lon_xl = excel_to_uv_components(p.excel_wind)
    print("Dimensions de lon_grid :", lon_xl.shape)
    print("Dimensions de lat_grid :", lat_xl.shape)
    print("Dimensions de u :", u_xl.shape)
    print("Dimensions de v :", v_xl.shape)


if __name__ == '__main__':

    bg = (47.25980827350693, -3.3287929957100237)
    hd = (47.596820491451524, -2.750893945710898)
    loc_nav = [bg[1], hd[1], bg[0], hd[0]]
    
    plot_grib([7], skip = 1, skip_vect_vent = 7, loc_nav=loc_nav)
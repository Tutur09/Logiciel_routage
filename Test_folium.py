import folium
import numpy as np

def plot_grib_folium(heure, position=None, route=None, context=None):
    """
    Plot GRIB data using Folium.
    
    Args:
        heure (list): List of time steps to visualize.
        position (tuple): Current position as (latitude, longitude).
        route (dict): Route data with 'lat' and 'lon' keys.
        context (str): Context for additional processing.
    """
    if not isinstance(heure, list):
        heure = [heure]
    
    # Créer une carte centrée sur une position par défaut
    center = [48.8566, 2.3522] if position is None else position
    m = folium.Map(location=center, zoom_start=6)

    # Exemple : Ajouter un marqueur pour la position actuelle
    if position:
        folium.Marker(
            location=position,
            popup="Position actuelle",
            icon=folium.Icon(color="red", icon="info-sign"),
        ).add_to(m)

    # Exemple de tracé de la route (si disponible)
    if route:
        folium.PolyLine(
            list(zip(route['lat'], route['lon'])),
            color="blue",
            weight=2.5,
            opacity=0.7,
            popup="Route suivie"
        ).add_to(m)

    # Exemple de visualisation de données GRIB simplifiée (vent)
    for h in heure:
        # Exemple de simulation des données (remplacez par vos données GRIB réelles)
        latitudes = np.linspace(44, 50, 10)
        longitudes = np.linspace(-5, 5, 10)
        wind_speed = np.random.uniform(10, 25, size=(10, 10))  # Simulez les vitesses de vent

        # Ajout de cercles pour représenter la vitesse du vent
        for i, lat in enumerate(latitudes):
            for j, lon in enumerate(longitudes):
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=wind_speed[i, j] / 5,  # Proportionnel à la vitesse
                    color="blue",
                    fill=True,
                    fill_opacity=0.6,
                    popup=f"Vent: {wind_speed[i, j]:.2f} nœuds",
                ).add_to(m)

    # Sauvegarder la carte dans un fichier HTML
    m.save("grib_map.html")
    print("La carte GRIB a été sauvegardée sous 'grib_map.html'. Ouvrez-la dans un navigateur.")

# Exemple d'appel
plot_grib_folium(
    heure=[0, 6, 12],
    position=(48.8566, 2.3522),
    route={'lat': [48.8566, 49, 50], 'lon': [2.3522, 3, 4]}
)

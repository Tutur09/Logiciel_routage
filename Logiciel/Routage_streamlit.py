import streamlit as st
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.colors as mcolors
import numpy as np
import xarray as xr
import Routage_calcul as rc
import Routage_Paramètres as p


def main():
    # Configuration de la navigation entre fenêtres
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Aller à", ["Visualisation", "Paramètres"])

    if page == "Paramètres":
        afficher_parametres()
    elif page == "Visualisation":
        afficher_visualisation()


def afficher_parametres():
    """Gère la configuration des paramètres dans l'application."""
    st.title("Configuration des paramètres")

    # Carte cliquable pour sélectionner les points de départ et d'arrivée
    st.subheader("Points de navigation (sélection sur carte)")
    m = folium.Map(location=[48.8566, 2.3522], zoom_start=5)  # Centré sur la France

    # Ajouter des marqueurs pour les positions initiale et finale par défaut
    start_marker = folium.Marker(location=p.position_initiale, popup="Point de départ", draggable=True)
    end_marker = folium.Marker(location=p.position_finale, popup="Point d'arrivée", draggable=True)
    start_marker.add_to(m)
    end_marker.add_to(m)

    # Intégrer la carte dans Streamlit
    output = st_folium(m, width=700, height=500)

    # Mettre à jour les positions en fonction des clics
    if output and "last_clicked" in output:
        if st.button("Définir comme point de départ"):
            p.position_initiale = output["last_clicked"]["lat"], output["last_clicked"]["lng"]
        elif st.button("Définir comme point d'arrivée"):
            p.position_finale = output["last_clicked"]["lat"], output["last_clicked"]["lng"]

    # Afficher les positions choisies
    st.write(f"Position initiale : {p.position_initiale}")
    st.write(f"Position finale : {p.position_finale}")

    # Paramètres avancés
    st.subheader("Paramètres avancés")
    p.pas_temporel = st.number_input("Pas temporel (en heures)", value=p.pas_temporel, min_value=1, step=1)
    p.pas_angle = st.number_input("Pas d'angle (en degrés)", value=p.pas_angle, min_value=1, step=1)
    p.tolerance_arrivée = st.number_input("Tolérance d'arrivée (en degrés)", value=p.tolerance_arrivée, format="%.6f")
    p.rayon_elemination = st.number_input("Rayon d'élimination (en degrés)", value=p.rayon_elemination, format="%.6f")

    st.success("Paramètres configurés. Passez à l'onglet 'Visualisation' pour exécuter le routage.")


def afficher_visualisation():
    """Affiche la visualisation des résultats du routage."""
    st.title("Visualisation de la route idéale")
    st.write("Cette application exécute le routage et affiche la route idéale avec les vents.")

    if st.button("Démarrer le routage"):
        st.write("**Calcul en cours...**")

        # Exécuter le routage
        result = rc.itere_jusqua_dans_enveloppe(
            p.position_initiale, p.position_finale,
            p.pas_temporel, p.pas_angle, p.tolerance_arrivée,
            p.loc_nav, live=False, enregistrement=False, streamlit=True
        )

        if result and 'lon' in result and 'lat' in result:
            chemin_lon = result['lon']
            chemin_lat = result['lat']
            afficher_carte(chemin_lon, chemin_lat)
        else:
            st.error("Aucun chemin n'a été retourné. Vérifiez les paramètres de routage.")


def afficher_carte(chemin_lon, chemin_lat):
    """Affiche la carte avec la route idéale et les données de vent."""
    # Configuration de la carte
    fig, ax = plt.subplots(figsize=(10, 8), subplot_kw={'projection': ccrs.PlateCarree()})
    ax.set_extent(p.loc_nav, crs=ccrs.PlateCarree())
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS.with_scale('10m'), linestyle=':')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
    ax.set_title("Route idéale avec les vents")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.gridlines(draw_labels=True)

    # Charger les données de vent
    if p.type == "grib":
        try:
            ds = xr.open_dataset(p.vent, engine='cfgrib')
            u10_specific = ds['u10'].isel(step=1).values
            v10_specific = ds['v10'].isel(step=1).values
            latitudes = ds['latitude'].values
            longitudes = ds['longitude'].values
        except Exception as e:
            st.error(f"Erreur lors de l'accès aux données GRIB : {e}")
            return
    else:
        st.error("Type de données non valide.")
        return

    # Afficher les données de vent
    cmap = mcolors.ListedColormap(p.colors_windy)
    norm = mcolors.BoundaryNorm(p.wind_speed_bins, cmap.N)
    skip = p.skip
    wind_speed = 1.852 * np.sqrt(u10_specific[::skip, ::skip]**2 + v10_specific[::skip, ::skip]**2)

    mesh = ax.pcolormesh(
        longitudes[::skip], latitudes[::skip], wind_speed,
        transform=ccrs.PlateCarree(), cmap=cmap, norm=norm, shading='auto'
    )

    skip_vect_vent = p.skip_vect_vent
    ax.barbs(
        longitudes[::skip_vect_vent], latitudes[::skip_vect_vent],
        1.852 * u10_specific[::skip_vect_vent, ::skip_vect_vent],
        1.852 * v10_specific[::skip_vect_vent, ::skip_vect_vent],
        length=5, pivot='middle', barbcolor='black', linewidth=0.6,
        transform=ccrs.PlateCarree()
    )

    cbar = plt.colorbar(mesh, ax=ax, orientation='vertical', pad=0.02, shrink=0.5)
    cbar.set_label("Vitesse du vent (nœuds)")

    # Tracer la route idéale
    ax.plot(chemin_lon, chemin_lat, color='red', linestyle='-', linewidth=2, transform=ccrs.PlateCarree(), label='Route idéale')
    ax.scatter(chemin_lon, chemin_lat, color='red', s=10, transform=ccrs.PlateCarree())
    ax.legend()

    # Afficher la carte
    st.pyplot(fig)
    st.success("Routage terminé avec succès !")


if __name__ == "__main__":
    main()

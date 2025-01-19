import streamlit as st
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.colors as mcolors
import numpy as np
import Routage_calcul as rc
import Routage_Paramètres as p
import xarray as xr

# Configuration de la navigation entre fenêtres
st.sidebar.title("Navigation")
page = st.sidebar.radio("Aller à", ["Visualisation", "Paramètres"])

# Page Paramètres
if page == "Paramètres":
    st.title("Configuration des paramètres")
    
    # Configuration des points de départ et d'arrivée
    st.subheader("Points de navigation")
    p.position_initiale = (
        st.number_input("Latitude du point de départ", value=p.position_initiale[0], format="%.6f"),
        st.number_input("Longitude du point de départ", value=p.position_initiale[1], format="%.6f")
    )
    p.position_finale = (
        st.number_input("Latitude du point d'arrivée", value=p.position_finale[0], format="%.6f"),
        st.number_input("Longitude du point d'arrivée", value=p.position_finale[1], format="%.6f")
    )

    # Configuration des paramètres avancés
    st.subheader("Paramètres avancés")
    p.pas_temporel = st.number_input("Pas temporel (en heures)", value=p.pas_temporel, min_value=1, step=1)
    p.pas_angle = st.number_input("Pas d'angle (en degrés)", value=p.pas_angle, min_value=1, step=1)
    p.tolerance_arrivée = st.number_input("Tolérance d'arrivée (en degrés)", value=p.tolerance_arrivée, format="%.6f")
    p.rayon_elemination = st.number_input("Rayon d'élimination (en degrés)", value=p.rayon_elemination, format="%.6f")

    st.success("Paramètres configurés. Passez à l'onglet 'Visualisation' pour exécuter le routage.")

# Page Visualisation
elif page == "Visualisation":
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
            heure = [p.heure_début]

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

            cmap = mcolors.ListedColormap(p.colors_windy)
            norm = mcolors.BoundaryNorm(p.wind_speed_bins, cmap.N)

            if p.type == "grib":
                try:
                    ds = xr.open_dataset(p.vent, engine='cfgrib')
                    u10_specific = ds['u10'].isel(step=int(1)).values
                    v10_specific = ds['v10'].isel(step=int(1)).values
                    latitudes = ds['latitude'].values
                    longitudes = ds['longitude'].values
                except Exception as e:
                    st.error(f"Erreur lors de l'accès aux données GRIB : {e}")
                    u10_specific, v10_specific, latitudes, longitudes = None, None, None, None
            else:
                st.error("Source de données non valide.")
                u10_specific, v10_specific, latitudes, longitudes = None, None, None, None

            if u10_specific is not None:
                skip = p.skip
                wind_speed = 1.852 * np.sqrt(u10_specific[::skip, ::skip]**2 + v10_specific[::skip, ::skip]**2)

                # Afficher les vents
                mesh = ax.pcolormesh(
                    longitudes[::skip], latitudes[::skip], wind_speed,
                    transform=ccrs.PlateCarree(), cmap=cmap, norm=norm, shading='auto'
                )

                # Ajouter les barbes pour la direction du vent
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

            # Afficher la carte dans Streamlit
            st.pyplot(fig)
            st.success("Routage terminé avec succès !")
        else:
            st.error("Aucun chemin n'a été retourné. Vérifiez les paramètres de routage.")

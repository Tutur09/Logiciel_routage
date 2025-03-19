import Routage_calcul as rc
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature


# Vérification de la courbure terrestre via la projection
def vérification_projection(latitudes = [10, 30, 50, 70], longitude = -3.0):
    points_initials = [(lat, longitude) for lat in latitudes]
    points_projetes = [rc.projection(point, 270, 100) for point in points_initials]

    longitudes_initials = [point[1] for point in points_initials]
    longitudes_projetes = [point[1] for point in points_projetes]

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(longitudes_initials, latitudes, color='blue', label="Points initiaux")
    ax.scatter(longitudes_projetes, latitudes, color='red', label="Points projetés (100 NM à l'ouest)")

    for i in range(len(latitudes)):
        ax.plot([longitudes_initials[i], longitudes_projetes[i]], [latitudes[i], latitudes[i]], 'k--')

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Projection à 100 NM vers l'Ouest en fonction de la latitude")
    ax.legend()
    ax.grid()

    plt.show()




if __name__ == "--main__":
    pass
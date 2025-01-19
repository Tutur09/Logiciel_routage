import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon
import rasterio
from rasterio.features import rasterize
import matplotlib.pyplot as plt

import Routage_Paramètres as p


# Charger les contours géographiques de la Bretagne
def load_brittany_geometry():
    url = "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_0_countries.zip"
    world = gpd.read_file(url, engine="fiona")

    # Filtrer pour la France
    france = world[world['NAME'] == 'France']

    # Définir la boîte englobante autour de la Bretagne
    brittany_bbox = Polygon([[-5.5, 46.5], [-5.5, 49.0], [-1.0, 49.0], [-1.0, 46.5], [-5.5, 46.5]])
    brittany = france[france.geometry.intersects(brittany_bbox)]

    return brittany

# Générer un masque raster terre/mer
def create_land_sea_mask(lat_min, lat_max, lon_min, lon_max, resolution):
    brittany = load_brittany_geometry()

    # Dimensions de la grille
    n_rows = int((lat_max - lat_min) * 60 * resolution)
    n_cols = int((lon_max - lon_min) * 60 * resolution)

    # Transformation pour associer la grille aux coordonnées géographiques
    transform = rasterio.transform.from_bounds(lon_min, lat_min, lon_max, lat_max, n_cols, n_rows)

    # Rasteriser la géométrie de la Bretagne
    mask = rasterize(
        [(geom, 1) for geom in brittany.geometry],  # Terre = 1
        out_shape=(n_rows, n_cols),
        transform=transform,
        fill=0,  # Mer = 0
        dtype='uint8',
    )

    return mask, transform

def save_mask_to_geotiff(mask, transform, filename):
    with rasterio.open(
        filename,
        'w',
        driver='GTiff',
        height=mask.shape[0],
        width=mask.shape[1],
        count=1,
        dtype='uint8',
        crs='EPSG:4326',
        transform=transform,
    ) as dst:
        dst.write(mask, 1)

def load_mask_from_geotiff(filename):
    with rasterio.open(filename) as src:
        mask = src.read(1)
        transform = src.transform
    return mask, transform

lat_min, lat_max = p.bg[0], p.hd[0]
lon_min, lon_max = p.bg[1], p.hd[1]
resolution = 10 

# mask, transform = create_land_sea_mask(lat_min, lat_max, lon_min, lon_max, resolution)
# save_mask_to_geotiff(mask, transform, "brittany_land_sea_mask.tif")
mask, transform = load_mask_from_geotiff("brittany_land_sea_mask.tif")

def get_point_value(point):
    (lat, lon) = point
    col, row = ~transform * (lon, lat)
    row, col = int(row), int(col)

    # Vérifier si les indices sont valides
    if 0 <= row < mask.shape[0] and 0 <= col < mask.shape[1]:
        return mask[row, col]
    else:
        raise ValueError("Le point est en dehors des limites du masque.")




if __name__ == "__main__":
    # Afficher le masque
    plt.figure(figsize=(10, 8))
    plt.imshow(mask, extent=[lon_min, lon_max, lat_min, lat_max], origin='upper', cmap='coolwarm')
    plt.colorbar(label='1 = Terre, 0 = Mer')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.title('Masque Terre/Mer pour la Bretagne')
    plt.show()

# Exemple : Vérifier un point
# longitude = -3.5
# latitude = 47.0
# value = get_point_value(longitude, latitude, mask, transform)
# print(value)
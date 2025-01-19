import requests
import rasterio
import matplotlib.pyplot as plt

# Configuration
API_URL = "https://public-api.meteofrance.fr/public/arome/1.0/wcs/MF-NWP-HIGHRES-AROME-001-FRANCE-WCS/GetCoverage"
API_KEY = "votre_api_key"
COVERAGE_ID = "votre_coverage_id"  # Remplacez par le coverageId valide
LAT_SUBSET = "lat(44:50)"
LON_SUBSET = "long(2:10)"
TIME_SUBSET = "time(2025-01-18T00:00:00Z)"

# Requête GetCoverage
params = {
    "service": "WCS",
    "version": "2.0.1",
    "request": "GetCoverage",
    "coverageId": COVERAGE_ID,
    "format": "image/tiff",
    "subset": [LAT_SUBSET, LON_SUBSET, TIME_SUBSET],
}
headers = {"apikey": API_KEY}

response = requests.get(API_URL, params=params, headers=headers)

# Sauvegarder le fichier TIFF
if response.status_code == 200:
    with open("arome_data.tiff", "wb") as f:
        f.write(response.content)
    print("Fichier téléchargé : arome_data.tiff")
else:
    print(f"Erreur : {response.status_code} - {response.text}")

# Charger et afficher le fichier TIFF
with rasterio.open("arome_data.tiff") as dataset:
    data = dataset.read(1)  # Lire la première couche
    plt.imshow(data, cmap="viridis")
    plt.colorbar(label="Valeur")
    plt.title("Données AROME")
    plt.show()

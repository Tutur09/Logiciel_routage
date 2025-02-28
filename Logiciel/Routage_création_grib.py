import sys
import Routage_Paramètres as p
from datetime import datetime, timezone
sys.path.append(r"C:\Users\arthu\OneDrive\Arthur\Programmation\API")
import meteofrance_grib # type: ignore



current_time = datetime.now(timezone.utc)  # Current time with UTC timezone
utc_hour = current_time.strftime("%H")    # Hour in UTC
date_mmjj = current_time.strftime("%m%d")  # Date au format MMJJ

output_grib_file = f"Données_vent\\METEOFRANCE_AROME_{utc_hour}Z_VENT_{date_mmjj}_.grib"
meteofrance_grib.grib_meteofrance(40, p.loc_nav, output_grib_file)

import sys
import Routage_Paramètres as p
from datetime import datetime, timezone
sys.path.append(r"C:\Users\arthu\OneDrive\Arthur\Programmation\Python\API_meteofrance")
import meteofrance_grib # type: ignore



current_time = datetime.now(timezone.utc)  # Current time with UTC timezone
utc_hour = current_time.strftime("%H")    # Hour in UTC
date_mmjj = current_time.strftime("%m%d")  # Date au format MMJJ

output_grib_file = f"Données_vent\\METEOFRANCE_AROME_{utc_hour}Z_VENT_{date_mmjj}_.grib"
# meteofrance_grib.grib_meteofrance(40, p.loc_nav, output_grib_file)

if __name__ == "__main__":
    bg = (47.25980827350693, -3.3287929957100237)
    hd = (47.596820491451524, -2.750893945710898)
    loc_nav = [bg[1], hd[1], bg[0], hd[0]]
    meteofrance_grib.grib_meteofrance(10, loc_nav, output_grib_file)
    

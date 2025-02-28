import Routage_calcul as rc
import Routage_Vent as rv
import Routage_Paramètres as p  
from copy import copy

points = rv.point_ini_fin(p.loc_nav)

# points_exemple_présentation = [(43.71, -8.65), (48.2, -4.74)] # 0226 Gascogne 8h

# points_arrivée_CD = [(45.285260681138624, -13.46112953695912), (46.45865441198225, -1.7840083504574855)]

# points = points_exemple_présentation

p.points = copy(points)

p.enable_prints()

rc.itere_jusqua_dans_enveloppe(points)
import Routage_calcul as rc
import Routage_Vent as rv
import Routage_Paramètres as p  
from copy import copy

points = rv.point_ini_fin(p.loc_nav)
p.points = copy(points)

p.enable_prints()

rc.itere_jusqua_dans_enveloppe(points)
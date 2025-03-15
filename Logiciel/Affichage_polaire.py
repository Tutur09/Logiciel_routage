import matplotlib.pyplot as plt
import matplotlib.cm as cm

import pandas as pd
import numpy as np
import Routage_calcul as rc
import Routage_Paramètres as p

plt.style.use('default')

def affiche_polaire(vitesses_vent):
    """
    Affiche les polaires en coordonnées 360° pour une vitesse de vent donnée.
    
    Arguments :
        vitesse_vent (float) : Vitesse de vent pour laquelle afficher les polaires.
    """
    # Récupération des données polaires pour la vitesse de vent donnée
    plt.figure(figsize=(8, 8))
    ax = plt.subplot(111, polar=True)
    
    norm = plt.Normalize(min(vitesses_vent), max(vitesses_vent))
    colors = cm.rainbow(norm(vitesses_vent))    
    
    for vitesse, color in zip(vitesses_vent, colors):
        result = rc.polaire(vitesse)
        if result is not None:
            angles = np.deg2rad(result.index)  # Conversion en radians
            angles_360 = np.concatenate([angles, 2 * np.pi - angles[::-1]])
            values_360 = np.concatenate([result.values, result.values[::-1]])

            ax.plot(angles_360, values_360, marker='o', linestyle='-', color=color, label=f'Vent: {vitesse} knt')

    ax.set_theta_zero_location("N")  # 0° au Nord
    ax.set_theta_direction(-1)       # Sens horaire
    
    ax.set_rlabel_position(0)  # Positionner les labels radiaux sur le haut
    rad_labels = [f"{int(val)} knt" for val in ax.get_yticks()]
    ax.set_yticklabels(rad_labels)
    
    # ax.set_title(f"Polaire {str(p.polaire)}", va='bottom')
    ax.legend(loc='right', bbox_to_anchor=(1.5, 1))
        
    plt.show()
        
affiche_polaire([5, 10, 15, 20, 25])
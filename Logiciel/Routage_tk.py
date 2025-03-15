import tkinter as tk
from tkinter import Frame, Menu, Toplevel, Label, Entry, Button, BooleanVar, Checkbutton, messagebox
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import Routage_Paramètres as p
import Routage_calcul as rc
import threading
import geocoder

class RoutageApp:
    def __init__(self, root):
        self.root = root
        
        icon = tk.PhotoImage(file=r"Exemples\Carte_vents_tempête.png")
        self.root.iconphoto(True, icon)

        self.root.title("Logiciel de Routage")
        self.root.geometry("1200x800")
        self.is_fullscreen = False
        self.routing_thread = None

        self.position_visible = BooleanVar(value=False)
        self.affichage_vent_couleur = BooleanVar(value=False)
        
        self.wind_cache = {}
        
        self.selection_button_default_bg = "#3498DB"  
        self.selection_button_active_bg = "#E74C3C"  
        
        self.wind_display_enabled = False



        # Navigation Menu
        self.create_menu()
        
        # Sidebar Controls
        self.sidebar = Frame(self.root, bg="#2C3E50", width=300)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        
        self.map_frame = Frame(self.root)
        self.map_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)  # S'assure qu'il prend toute la place disponible


        
        # Matplotlib Figure
        self.fig, self.ax = plt.subplots(figsize=(1, 1), dpi=100, subplot_kw={"projection": ccrs.PlateCarree()})
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.map_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        
        self.zoom_factor = 1.2
        self.drag_start = None
        
        self.initialize_map()
        self.update_computer_position()
        
        # Buttons
        self.create_sidebar_buttons()
        
        # User Points
        p.points = []
        self.point_selection_enabled = False
        
        self.canvas.mpl_connect("scroll_event", self.zoom)
        self.canvas.mpl_connect("button_press_event", self.on_left_press)   
        self.canvas.mpl_connect("button_release_event", self.on_release)
        self.canvas.mpl_connect("motion_notify_event", self.on_left_drag)
        
        self.map_frame.bind("<Configure>", self.resize_canvas)
        
        # Touches
        self.ctrl_pressed = False
        
        self.canvas.mpl_connect("key_press_event", self.on_key_press)
        self.canvas.mpl_connect("key_release_event", self.on_key_release)
        
        self.canvas.mpl_connect("scroll_event", self.zoom)

    def create_menu(self):
        menu_bar = Menu(self.root)
        self.root.config(menu=menu_bar)
        
        navigation_menu = Menu(menu_bar, tearoff=0)
        navigation_menu.add_command(label="Accueil", command=self.reset_points, font=(("Arial", 14)))
        
        routage_menu = Menu(menu_bar, tearoff=0)
        routage_menu.add_command(label="Lancer routage", command=self.execute_routing)
        
        affichage_menu = Menu(menu_bar, tearoff=0)
        affichage_menu.add_checkbutton(
            label="Position",
            variable=self.position_visible,
            command=self.toggle_position,  # fonction qui gère l'action à la modification
            font=(("Arial", 14))
        )
        affichage_menu.add_checkbutton(
            label="Vent coloré",
            variable=self.affichage_vent_couleur,
            font=(("Arial", 14))
        )
        
        menu_bar.add_cascade(label = "Navigation", menu=navigation_menu, )
        menu_bar.add_cascade(label = "Paramètres", command=self.open_param_window)
        menu_bar.add_cascade(label = "Routage", menu = routage_menu)
        menu_bar.add_cascade(label = "Affichage", menu = affichage_menu)
    
    def create_sidebar_buttons(self):
        # Étiquette et slider pour choisir l'heure du vent
        self.wind_value_label = tk.Label(self.sidebar, text="Heure du vent: 0", font=("Arial", 14, "bold"), fg="white", bg="#2C3E50")
        self.wind_value_label.pack(pady=10, padx=20, fill=tk.X)

        self.wind_slider = tk.Scale(self.sidebar, from_=0, to=p.nb_step - 1, orient=tk.HORIZONTAL, command=self.update_wind_value, font=("Arial", 12))
        self.wind_slider.pack(pady=10, padx=20, fill=tk.X)

        # Configuration commune pour les boutons
        button_config = {"font": ("Arial", 14, "bold"), "bg": self.selection_button_default_bg, "fg": "white", "height": 2, "width": 20}

        # Bouton toggle pour l'affichage du vent
        self.wind_button = tk.Button(self.sidebar, text="Afficher Vent", command=self.toggle_wind_display, **button_config)
        self.wind_button.pack(pady=10, padx=20)

        # Bouton pour la sélection des points (reste inchangé)
        self.selection_button = tk.Button(self.sidebar, text="Sélectionner Points", command=self.toggle_point_selection, **button_config)
        self.selection_button.pack(pady=10, padx=20)

        tk.Button(self.sidebar, text="Lancer Routage", command=self.execute_routing, **button_config).pack(pady=10, padx=20)
        tk.Button(self.sidebar, text="Réinitialiser", command=self.reset_points, **button_config).pack(pady=10, padx=20)
        tk.Button(self.sidebar, text="Quitter", command=self.root.quit, **{**button_config, "bg": "#E74C3C"}).pack(pady=10, padx=20)

    def initialize_map(self):
        """Affiche la carte centrée sur un point spécifique avec une zone définie autour."""
        # Définition du point central (exemple : centre de la Bretagne)
        center_lat, center_lon = 48.0, -4.0  # Remplace par les coordonnées désirées

        # Définition de la zone autour du point central (10° en lat/lon)
        delta_lat = 5.0  # Écart en latitude
        delta_lon = 5.0  # Écart en longitude

        # Définition de la nouvelle étendue
        xmin, xmax = center_lon - delta_lon, center_lon + delta_lon
        ymin, ymax = center_lat - delta_lat, center_lat + delta_lat

        # Appliquer l'étendue centrée
        self.ax.set_extent([xmin, xmax, ymin, ymax], crs=ccrs.PlateCarree())

        # Ajouter les éléments géographiques
        self.ax.add_feature(cfeature.COASTLINE.with_scale("10m"), linewidth=1)
        self.ax.add_feature(cfeature.BORDERS.with_scale("10m"), linestyle=":")
        self.ax.add_feature(cfeature.LAND, facecolor="lightgray")
        self.ax.add_feature(cfeature.OCEAN, facecolor="lightblue")

        # Supprimer toutes les marges et centrer
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.ax.set_position([0, 0, 1, 1])

        self.canvas.draw_idle()
        
    def resize_canvas(self, event):
        """Empêche l'ajustement automatique pour garder la carte centrée sur le point fixe."""
        dpi = self.canvas.figure.dpi
        self.fig.set_size_inches(event.width / dpi, event.height / dpi, forward=True)
        self.canvas.draw_idle()

    def zoom(self, event):
        # Vérifier si on utilise la molette ou le trackpad (les valeurs peuvent être inversées)
        if event.step > 0:  # Zoom avant
            factor = 1 / self.zoom_factor
        elif event.step < 0:  # Zoom arrière
            factor = self.zoom_factor
        else:
            return

        # Appliquer le facteur de zoom sur les limites actuelles
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()

        self.ax.set_xlim([
            event.xdata - (event.xdata - xlim[0]) * factor,
            event.xdata + (xlim[1] - event.xdata) * factor
        ])
        self.ax.set_ylim([
            event.ydata - (event.ydata - ylim[0]) * factor,
            event.ydata + (ylim[1] - event.ydata) * factor
        ])
        
        self.canvas.draw_idle()
        
    def on_key_press(self, event):
        if event.key == "control":
            self.ctrl_pressed = True

    def on_key_release(self, event):
        if event.key == "control":
            self.ctrl_pressed = False

    def on_left_press(self, event):
        if event.button == 1 :#and self.ctrl_pressed:
            self.drag_start = (event.x, event.y, list(self.ax.get_xlim()), list(self.ax.get_ylim()))

    def on_left_drag(self, event):
        if self.drag_start is None : #or not self.ctrl_pressed:
            return

        dx = (self.drag_start[0] - event.x) / (self.canvas.get_tk_widget().winfo_width() / (self.drag_start[2][1] - self.drag_start[2][0]))
        dy = (self.drag_start[1] - event.y) / (self.canvas.get_tk_widget().winfo_height() / (self.drag_start[3][1] - self.drag_start[3][0]))

        self.ax.set_xlim([self.drag_start[2][0] + dx, self.drag_start[2][1] + dx])
        self.ax.set_ylim([self.drag_start[3][0] + dy, self.drag_start[3][1] + dy])
        
        self.canvas.draw_idle()

    def on_release(self, event):
        self.drag_start = None

    def toggle_wind_display(self):
        if not self.wind_display_enabled:
            self.wind_display_enabled = True
            self.wind_button.config(bg=self.selection_button_active_bg)
            self.display_wind()  # Affichage immédiat avec la valeur actuelle du slider
        else:
            self.wind_display_enabled = False
            self.wind_button.config(bg=self.selection_button_default_bg)
            self.clear_wind_display()
        self.canvas.draw_idle()

    def update_wind_value(self, value):
        self.wind_value_label.config(text=f"Heure du vent: {value}")
        if self.wind_display_enabled:
            self.display_wind()

    def compute_wind_display_data(self, hour):
        """
        Calcule et renvoie les données de vent pour l'heure donnée.
        Ces données incluent les sous-échantillonnages pour le pcolormesh et les barbs.
        """
        import Routage_Vent as rv  # Utilise le module de vent pour accéder aux données
        if p.type == "grib":
            ds = rv.ds  # On suppose que ds est déjà ouvert dans le module
            u10_specific = ds['u10'].isel(step=int(hour)).values
            v10_specific = ds['v10'].isel(step=int(hour)).values
            latitudes = ds['latitude'].values
            longitudes = ds['longitude'].values
        elif p.type == "excel":
            u10_specific = rv.u_xl[0]
            v10_specific = rv.v_xl[0]
            latitudes = rv.lat_xl
            longitudes = rv.lon_xl
        else:
            raise ValueError("Type de données non supporté.")

        skip = p.skip
        skip_vect = p.skip_vect_vent

        # Sous-échantillonnage pour la carte
        latitudes_sub = latitudes[::skip]
        longitudes_sub = longitudes[::skip]
        u10_sub = u10_specific[::skip, ::skip]
        v10_sub = v10_specific[::skip, ::skip]
        wind_speed = 1.852 * np.sqrt(u10_sub**2 + v10_sub**2)

        # Sous-échantillonnage pour les barbs
        latitudes_barb = latitudes[::skip_vect]
        longitudes_barb = longitudes[::skip_vect]
        u10_barb = u10_specific[::skip_vect, ::skip_vect]
        v10_barb = v10_specific[::skip_vect, ::skip_vect]

        return {
            "latitudes": longitudes_sub,  # Attention : pcolormesh attend souvent des coordonnées X = longitudes, Y = latitudes
            "longitudes": latitudes_sub,
            "wind_speed": wind_speed,
            "latitudes_barb": latitudes_barb,
            "longitudes_barb": longitudes_barb,
            "u10_barb": u10_barb,
            "v10_barb": v10_barb,
        }

    def display_wind(self):
        try:
            hour = int(self.wind_slider.get())
            # Sauvegarder les limites actuelles
            current_xlim = self.ax.get_xlim()
            current_ylim = self.ax.get_ylim()
            
            # Effacer uniquement les couches qui ne sont pas le fond de carte ni les points
            # Par exemple, supprimer les anciennes couches de vent si elles existent
            if hasattr(self, "wind_mappable"):
                self.wind_mappable.remove()
                del self.wind_mappable
            if hasattr(self, "wind_barbs"):
                self.wind_barbs.remove()
                del self.wind_barbs

            # Ne pas effacer tout l'axe afin de conserver l'étendue contractée
            # self.ax.cla() n'est pas utilisé ici

            # Redessiner les caractéristiques géographiques si nécessaire
            # (Si elles sont déjà présentes, pas besoin de les réajouter)
            # Vous pouvez aussi vérifier ou redessiner uniquement si c'est indispensable.

            # Restaurer les limites sauvegardées
            self.ax.set_xlim(current_xlim)
            self.ax.set_ylim(current_ylim)

            # (Optionnel) Redessiner les points sélectionnés
            for pt in p.points:
                lat, lon = pt
                color = "green" if p.points.index(pt) == 0 else "red" if p.points.index(pt) == 1 else "black"
                self.ax.scatter(lon, lat, color=color, marker="x", s=100, transform=ccrs.PlateCarree())

            # Utiliser le cache pour éviter de recalculer
            if hour not in self.wind_cache:
                self.wind_cache[hour] = self.compute_wind_display_data(hour)
            data = self.wind_cache[hour]

            # Tracer le pcolormesh pour l'intensité du vent
            if self.affichage_vent_couleur.get():
                cmap = mcolors.ListedColormap(p.colors_windy)
                norm = mcolors.BoundaryNorm(p.wind_speed_bins, cmap.N)
                self.wind_mappable = self.ax.pcolormesh(
                    data["latitudes"], data["longitudes"], data["wind_speed"],
                    transform=ccrs.PlateCarree(), cmap=cmap, norm=norm, shading='auto'
                )

            # Tracer les barbs pour la direction du vent
            self.wind_barbs = self.ax.barbs(
                data["longitudes_barb"], data["latitudes_barb"],
                1.852 * data["u10_barb"], 1.852 * data["v10_barb"],
                length=5, pivot="middle", barbcolor="black", linewidth=0.6,
                transform=ccrs.PlateCarree()
            )

            self.canvas.draw_idle()
        except ValueError:
            messagebox.showwarning("Erreur", "La valeur du slider est invalide.")

    def clear_wind_display(self):
        # Retirer la couche de vent si elle existe
        if hasattr(self, "wind_mappable"):
            self.wind_mappable.remove()
            del self.wind_mappable
        if hasattr(self, "wind_barbs"):
            self.wind_barbs.remove()
            del self.wind_barbs

        # Optionnel : vous pouvez redessiner les points ou autres éléments statiques
        for pt in p.points:
            lat, lon = pt
            color = "green" if p.points.index(pt) == 0 else "red" if p.points.index(pt) == 1 else "black"
            self.ax.scatter(lon, lat, color=color, marker="x", s=100, transform=ccrs.PlateCarree())

        self.canvas.draw_idle()

    def enable_point_selection(self):
        self.point_selection_enabled = True
        self.click_id = self.canvas.mpl_connect("button_press_event", self.on_click)

    def toggle_point_selection(self):
        # Si la sélection n'est pas activée, on l'active et on change la couleur du bouton
        if not self.point_selection_enabled:
            self.point_selection_enabled = True
            self.selection_button.config(bg=self.selection_button_active_bg)
            self.click_id = self.canvas.mpl_connect("button_press_event", self.on_click)
        else:
            # Si déjà activée, on la désactive, on retire le binding et on remet le bouton à sa couleur initiale
            self.point_selection_enabled = False
            if self.click_id is not None:
                self.canvas.mpl_disconnect(self.click_id)
                self.click_id = None
            self.selection_button.config(bg=self.selection_button_default_bg)
        self.canvas.draw_idle()

    def clear_dynamic_elements(self):
        # Supprimer les objets dynamiques dans les collections (pcolormesh, etc.)
        for coll in list(self.ax.collections):
            if not getattr(coll, "_is_static", False):
                coll.remove()

        # Supprimer les lignes (routes, enveloppes, etc.)
        for line in list(self.ax.lines):
            if not getattr(line, "_is_static", False):
                line.remove()

        # Vous pouvez aussi faire de même pour les textes ou autres artistes
        self.canvas.draw_idle()

    def reset_points(self):
        if messagebox.askyesno("Confirmation", "Réinitialiser tous les points ?"):
            # Réinitialiser la liste des points
            p.points = []

            # Sauvegarder l'étendue actuelle (dimensions de la vue)
            current_extent = self.ax.get_extent(crs=ccrs.PlateCarree())

            # Effacer uniquement les éléments dynamiques
            self.clear_dynamic_elements()

            # (Optionnel) Vous pouvez également mettre à jour d'autres éléments dynamiques
            # par exemple, réafficher le marqueur de position
            self.update_computer_position()

            # Restaurer l'étendue sauvegardée pour conserver le zoom/pan
            self.ax.set_extent(current_extent, crs=ccrs.PlateCarree())
            self.canvas.draw_idle()

    def on_click(self, event):
        if not self.point_selection_enabled:
            return
        data_coord = self.ax.transData.inverted().transform((event.x, event.y))
        lon, lat = data_coord
        p.points.append((lat, lon))
        artist = self.ax.scatter(lon, lat,
                                color="green" if len(p.points) == 1 else "red" if len(p.points) == 2 else "black",
                                marker="x", s=100, transform=ccrs.PlateCarree(),
                                label="Point sélectionné")
        # Initialiser la liste si nécessaire et enregistrer l'objet
        if not hasattr(self, "selection_artists"):
            self.selection_artists = []
        self.selection_artists.append(artist)
        self.canvas.draw_idle()

    def execute_routing(self):
        if self.point_selection_enabled:
            self.toggle_point_selection()
        if len(p.points) < 2:
            messagebox.showwarning("Erreur", "Veuillez sélectionner au moins deux points.")
            return
        # Désactiver la sélection de points en déconnectant le binding
        self.point_selection_enabled = False
        if hasattr(self, "click_id"):
            self.canvas.mpl_disconnect(self.click_id)
        threading.Thread(target=self.run_routing, daemon=True).start()

    def run_routing(self):
        rc.itere_jusqua_dans_enveloppe_tk(p.points, self.ax, self.canvas)
        self.canvas.draw_idle()
        self.root.update_idletasks()  # Remplace self.controller.root.update_idletasks()

    def open_param_window(self):
        param_window = Toplevel(self.root)
        param_window.title("Modifier les paramètres")
        param_window.geometry("400x500")
        
        # Dictionnaire incluant des paramètres numériques et booléens
        params = {
            "pas_temporel": p.pas_temporel, 
            "pas_angle": p.pas_angle, 
            "rayon élimination points": p.rayon_elemination,
            "Tolérance arrivée": p.tolerance_arrivée,
            "affichage des enveloppes": p.enveloppe,
            "Contact terrestre": p.land_contact
        }
        
        self.entries = {}      # Pour les Entry
        self.bool_vars = {}    # Pour les Checkbutton associés aux booléens

        row = 0
        for param, value in params.items():
            Label(param_window, text=param, font=("Arial", 14)).grid(row=row, column=0, padx=10, pady=5)
            if isinstance(value, bool):
                # Création d'un Checkbutton pour les booléens
                var = tk.BooleanVar(value=value)
                chk = tk.Checkbutton(param_window, variable=var, font=("Arial", 14))
                chk.grid(row=row, column=1, padx=10, pady=5)
                self.bool_vars[param] = var
            else:
                # Création d'un Entry pour les autres types (numériques)
                entry = Entry(param_window, font=("Arial", 14), width=15)
                entry.insert(0, str(value))
                entry.grid(row=row, column=1, padx=10, pady=5)
                self.entries[param] = entry
            row += 1
        
        Button(param_window, text="Enregistrer", 
            command=lambda: (self.save_params(), param_window.destroy()),
            font=("Arial", 14)).grid(row=row, columnspan=2, pady=10)

    def save_params(self):
        try:
            # Pour les paramètres numériques
            for param, widget in self.entries.items():
                value = widget.get()
                if param == "pas_angle":
                    setattr(p, param, int(float(value)))
                else:
                    setattr(p, param, float(value))
            # Pour les paramètres booléens
            for param, var in self.bool_vars.items():
                setattr(p, param, var.get())
        except ValueError as e:
            messagebox.showerror("Erreur", f"Valeur invalide : {e}")

    def update_computer_position(self):
        # Si l'affichage de la position est désactivé, on ne met pas à jour le marqueur
        if not self.position_visible.get():
            # On peut aussi supprimer le marqueur s'il existe
            if hasattr(self, "computer_marker"):
                try:
                    self.computer_marker.remove()
                except Exception as e:
                    print("Erreur lors de la suppression du marqueur:", e)
            self.canvas.draw_idle()
            # Planifier la prochaine vérification sans recréer le marqueur
            self.root.after(5000, self.update_computer_position)
            return

        def get_current_location():
            g = geocoder.ip('me')
            if g.ok:
                return g.latlng  # renvoie [latitude, longitude]
            else:
                return None

        loc = get_current_location()
        if loc is not None:
            lat, lon = loc
            # Supprimez le marqueur précédent s'il existe déjà
            if hasattr(self, "computer_marker"):
                try:
                    self.computer_marker.remove()
                except Exception as e:
                    pass
            # Ajoutez un marqueur bleu pour représenter la position de l'ordinateur
            self.computer_marker = self.ax.scatter(
                lon, lat,
                color="blue", marker="o", s=100,
                transform=ccrs.PlateCarree(),
                label="Ma position"
            )
            # On peut mettre à jour la légende si besoin
            self.ax.legend()
            self.canvas.draw_idle()
        # Actualise la position toutes les 5 secondes
        self.root.after(5000, self.update_computer_position)
    
    def toggle_position(self):
        if self.position_visible.get():
            print("Affichage de la position activé")
            self.update_computer_position() 
        else:
            print("Affichage de la position désactivé")
            if hasattr(self, "computer_marker"):
                try:
                    self.computer_marker.remove()
                except Exception as e:
                    print("Erreur lors de la suppression du marqueur:", e)
                self.canvas.draw_idle()
                        
if __name__ == "__main__":
    root = tk.Tk()
    app = RoutageApp(root)
    root.mainloop()
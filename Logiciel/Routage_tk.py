import tkinter as tk
from tkinter import Frame, Menu, Toplevel, Label, Entry, Button, BooleanVar, Checkbutton, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import Routage_Paramètres as p
import Routage_calcul as rc
import Routage_Vent as rv
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
        
        # Main Content
        self.map_frame = Frame(self.root)
        self.map_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
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

        self.wind_slider = tk.Scale(self.sidebar, from_=0, to=23, orient=tk.HORIZONTAL, command=self.update_wind_value, font=("Arial", 12))
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
        # Ne pas réinitialiser les marges ici pour éviter de modifier la mise en page
        self.ax.set_extent(p.loc_nav, crs=ccrs.PlateCarree())
        self.ax.add_feature(cfeature.COASTLINE.with_scale("10m"), linewidth=1)
        self.ax.add_feature(cfeature.BORDERS.with_scale("10m"), linestyle=":")
        self.ax.add_feature(cfeature.LAND, facecolor="lightgray")
        self.ax.add_feature(cfeature.OCEAN, facecolor="lightblue")
        self.canvas.draw_idle()
    
    def resize_canvas(self, event):
        available_width = event.width
        available_height = event.height
        container_ratio = available_width / available_height

        xmin, xmax, ymin, ymax = p.loc_nav
        map_ratio = (xmax - xmin) / (ymax - ymin)

        # Ajustement de l'étendue selon le ratio du conteneur
        if container_ratio > map_ratio:
            # Le conteneur est plus large que le ratio d'origine.
            # On étend l'axe x pour remplir l'espace sans changer l'axe y.
            new_width = (ymax - ymin) * container_ratio
            x_center = (xmax + xmin) / 2
            new_xmin = x_center - new_width / 2
            new_xmax = x_center + new_width / 2
            new_extent = [new_xmin, new_xmax, ymin, ymax]
        else:
            # Le conteneur est plus étroit que le ratio d'origine.
            # On étend l'axe y pour remplir l'espace sans changer l'axe x.
            new_height = (xmax - xmin) / container_ratio
            y_center = (ymax + ymin) / 2
            new_ymin = y_center - new_height / 2
            new_ymax = y_center + new_height / 2
            new_extent = [xmin, xmax, new_ymin, new_ymax]

        # Appliquer la nouvelle étendue en conservant la projection
        self.ax.set_extent(new_extent, crs=ccrs.PlateCarree())

        # Optionnel : redimensionner la figure pour correspondre exactement à la zone disponible
        dpi = self.canvas.figure.dpi
        self.fig.set_size_inches(available_width / dpi, available_height / dpi, forward=True)

        # Laisser l'axe occuper toute la figure
        self.ax.set_position([0, 0, 1, 1])
        self.canvas.draw_idle()

    def zoom(self, event):
        # Ne zoomer que si la touche Ctrl est enfoncée
        if not self.ctrl_pressed:
            return

        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        factor = 1 / self.zoom_factor if event.step > 0 else self.zoom_factor
        self.ax.set_xlim([event.xdata - (event.xdata - xlim[0]) * factor,
                        event.xdata + (xlim[1] - event.xdata) * factor])
        self.ax.set_ylim([event.ydata - (event.ydata - ylim[0]) * factor,
                        event.ydata + (ylim[1] - event.ydata) * factor])
        self.canvas.draw_idle()
        
    def on_key_press(self, event):
        if event.key == "control":
            self.ctrl_pressed = True
            print("Ctrl appuyé")

    def on_key_release(self, event):
        if event.key == "control":
            self.ctrl_pressed = False
            # print("Ctrl relâché")

    def on_left_press(self, event):
        if event.button == 1 :#and self.ctrl_pressed:
            self.drag_start = (event.x, event.y, list(self.ax.get_xlim()), list(self.ax.get_ylim()))
            print("Début du drag")

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
        """Active/désactive l'affichage du vent en mode toggle."""
        if not self.wind_display_enabled:
            self.wind_display_enabled = True
            self.wind_button.config(bg=self.selection_button_active_bg)
            # Affiche immédiatement le vent avec la valeur actuelle du slider
            self.display_wind()
        else:
            self.wind_display_enabled = False
            self.wind_button.config(bg=self.selection_button_default_bg)
            # Efface l'affichage du vent tout en conservant le fond de carte
            self.clear_wind_display()
        self.canvas.draw_idle()

    def update_wind_value(self, value):
        """Mise à jour de l'étiquette avec la valeur actuelle du slider et actualisation du vent si activé."""
        self.wind_value_label.config(text=f"Heure du vent: {value}")
        # Si le toggle est activé, actualiser l'affichage du vent
        if self.wind_display_enabled:
            self.display_wind()

    def display_wind(self):
        try:
            hour = int(self.wind_slider.get())
            # Sauvegarder l'étendue actuelle pour conserver le cadrage
            current_xlim = self.ax.get_xlim()
            current_ylim = self.ax.get_ylim()

            # On vide uniquement les anciennes couches de vent (par exemple, on peut redessiner la carte)
            self.ax.cla()
            self.initialize_map()
            self.ax.set_xlim(current_xlim)
            self.ax.set_ylim(current_ylim)

            # (Optionnel) Redessiner les points sélectionnés, s'ils existent
            for pt in p.points:
                lat, lon = pt
                color = "green" if p.points.index(pt) == 0 else "red" if p.points.index(pt) == 1 else "black"
                self.ax.scatter(lon, lat, color=color, marker="x", s=100, transform=ccrs.PlateCarree())

            # Afficher le vent pour l'heure choisie
            import Routage_Vent as rv  # Assurez-vous que ce module est bien importé
            rv.plot_wind_tk(self.ax, self.canvas, p.loc_nav, step_indices=[hour], couleur=self.affichage_vent_couleur.get())
            self.canvas.draw_idle()
        except ValueError:
            messagebox.showwarning("Erreur", "La valeur du slider est invalide.")

    def clear_wind_display(self):
        """Efface l'affichage du vent sans réinitialiser l'ensemble de la carte."""
        current_xlim = self.ax.get_xlim()
        current_ylim = self.ax.get_ylim()
        self.ax.cla()
        self.initialize_map()
        self.ax.set_xlim(current_xlim)
        self.ax.set_ylim(current_ylim)
        # (Optionnel) Redessiner les points déjà sélectionnés
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

    def reset_points(self):
        if messagebox.askyesno("Confirmation", "Réinitialiser tous les points ?"):
            p.points = []
            # Capturer l'étendue actuelle de la carte pour la conserver
            current_extent = self.ax.get_extent(crs=ccrs.PlateCarree())
            # Effacer l'axe
            self.ax.clear()
            # Réinitialiser la carte sans modifier son espace occupé
            self.initialize_map()
            # Restaurer l'étendue capturée
            self.ax.set_extent(current_extent, crs=ccrs.PlateCarree())
            # Réafficher le marqueur de position (en bleu)
            self.update_computer_position()
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
        
        params = {"pas_temporel": p.pas_temporel, "pas_angle": p.pas_angle, "tolerance": p.tolerance}
        self.entries = {}
        
        for row, (param, value) in enumerate(params.items()):
            Label(param_window, text=param).grid(row=row, column=0, padx=10, pady=5)
            entry = Entry(param_window)
            entry.insert(0, str(value))
            entry.grid(row=row, column=1, padx=10, pady=5)
            self.entries[param] = entry
        
        Button(param_window, text="Enregistrer", command=self.save_params).grid(row=row+1, columnspan=2, pady=10)
    
    def save_params(self):
        for param, widget in self.entries.items():
            setattr(p, param, float(widget.get()))
        messagebox.showinfo("Succès", "Paramètres mis à jour.")
    
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
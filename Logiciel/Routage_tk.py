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

class RoutageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Logiciel de Routage")
        self.root.geometry("1200x800")
        self.is_fullscreen = False
        self.routing_thread = None

        # Navigation Menu
        self.create_menu()
        
        # Sidebar Controls
        self.sidebar = Frame(self.root, bg="#2C3E50", width=300)  # Augmente la largeur de la barre
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
    
    def create_menu(self):
        menu_bar = Menu(self.root)
        self.root.config(menu=menu_bar)
        
        navigation_menu = Menu(menu_bar, tearoff=0)
        navigation_menu.add_command(label="Accueil", command=self.reset_points)
        menu_bar.add_cascade(label="Navigation", menu=navigation_menu)
        
        menu_bar.add_cascade(label="Paramètres", command=self.open_param_window)
    
    def create_sidebar_buttons(self):
        self.wind_hour_var = tk.StringVar()
        tk.Label(self.sidebar, text="Heure du vent:", font=("Arial", 14, "bold"), fg="white", bg="#2C3E50").pack(pady=10, padx=20, fill=tk.X)
        self.wind_hour_entry = tk.Entry(self.sidebar, textvariable=self.wind_hour_var, font=("Arial", 14))
        self.wind_hour_entry.pack(pady=10, padx=20, fill=tk.X)

        # Agrandir les boutons avec du padding et une plus grande police
        button_config = {"font": ("Arial", 14, "bold"), "bg": "#3498DB", "fg": "white", "height": 2, "width": 20}

        tk.Button(self.sidebar, text="Afficher Vent", command=self.display_wind, **button_config).pack(pady=10, padx=20)
        tk.Button(self.sidebar, text="Sélectionner Points", command=self.enable_point_selection, **button_config).pack(pady=10, padx=20)
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
        # On ne fait plus : self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.canvas.draw_idle()

    
    def resize_canvas(self, event):
        # Dimensions disponibles dans le cadre de la carte
        available_width = event.width
        available_height = event.height
        container_ratio = available_width / available_height

        # On récupère l'étendue de référence de la carte
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
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        factor = 1 / self.zoom_factor if event.step > 0 else self.zoom_factor
        self.ax.set_xlim([event.xdata - (event.xdata - xlim[0]) * factor,
                          event.xdata + (xlim[1] - event.xdata) * factor])
        self.ax.set_ylim([event.ydata - (event.ydata - ylim[0]) * factor,
                          event.ydata + (ylim[1] - event.ydata) * factor])
        self.canvas.draw_idle()
    
    def on_left_press(self, event):
        if event.button == 1:  # Clic gauche pour déplacer
            self.drag_start = (event.x, event.y, list(self.ax.get_xlim()), list(self.ax.get_ylim()))
    
    def on_release(self, event):
        self.drag_start = None
    
    def on_left_drag(self, event):
        if self.drag_start is None or event.x is None or event.y is None:
            return

        dx = (self.drag_start[0] - event.x) / (self.canvas.get_tk_widget().winfo_width() / (self.drag_start[2][1] - self.drag_start[2][0]))
        dy = (self.drag_start[1] - event.y) / (self.canvas.get_tk_widget().winfo_height() / (self.drag_start[3][1] - self.drag_start[3][0]))

        self.ax.set_xlim([self.drag_start[2][0] + dx, self.drag_start[2][1] + dx])
        self.ax.set_ylim([self.drag_start[3][0] + dy, self.drag_start[3][1] + dy])
        
        self.canvas.draw_idle()

    def display_wind(self):
        try:
            hour = int(self.wind_hour_var.get())
            # Ajoute le vent sans réinitialiser la carte
            rv.plot_wind_tk(self.ax, self.canvas, p.loc_nav, step_indices=[hour])
            self.canvas.draw_idle()
        except ValueError:
            messagebox.showwarning("Erreur", "Veuillez entrer une heure valide.")


    def enable_point_selection(self):
        self.point_selection_enabled = True
        self.canvas.get_tk_widget().bind("<Button-1>", self.on_click)
    
    def reset_points(self):
        if messagebox.askyesno("Confirmation", "Réinitialiser tous les points ?"):
            p.points = []
            self.ax.clear()
            self.initialize_map()
            self.canvas.draw_idle()
    
    def on_click(self, event):
        if not self.point_selection_enabled:
            return
        
        x, y = self.ax.transData.inverted().transform((event.x, self.canvas.get_tk_widget().winfo_height() - event.y))
        p.points.append((y, x))
        color = "green" if len(p.points) == 1 else "red" if len(p.points) == 2 else "black"
        self.ax.scatter(x, y, color=color, marker="x", s=100, transform=ccrs.PlateCarree())
        self.canvas.draw_idle()
    
    def execute_routing(self):
        if len(p.points) < 2:
            messagebox.showwarning("Erreur", "Veuillez sélectionner au moins deux points.")
            return
        
        threading.Thread(target=self.run_routing, daemon=True).start()
    
    def run_routing(self):
        rc.itere_jusqua_dans_enveloppe_tk(p.points, self.ax, self.canvas)
        self.canvas.draw_idle()
        self.controller.root.update_idletasks()
    
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


class AccueilPage(Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent, bg="#2C3E50")
        self.controller = controller
        
        label = tk.Label(self, text="Bienvenue dans le logiciel de routage", font=("Arial", 20, "bold"), fg="white", bg="#2C3E50")
        label.pack(pady=30)
        
        btn_routage = tk.Button(self, text="Routage", font=("Arial", 18, "bold"), bg="#3498DB", fg="white", relief="flat", width=25, height=4,
                                padx=15, pady=15, command=lambda: controller.show_frame("RoutagePage"))
        btn_routage.pack(pady=20)
        
        btn_exit = tk.Button(self, text="Quitter", font=("Arial", 18, "bold"), bg="#E74C3C", fg="white", relief="flat", width=25, height=4,
                             padx=15, pady=15, command=controller.root.quit)
        btn_exit.pack(pady=20)

class RoutagePage(Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        self.controller = controller
        
        # Création du menu
        self.create_menu()
        
        # Conteneur principal pour la carte
        self.map_frame = Frame(self)
        self.sidebar.pack_propagate(False)
        self.map_frame.pack(fill=tk.BOTH, expand=True)

        # Création de la figure Matplotlib pour Tkinter
        self.fig, self.ax = plt.subplots(figsize=(12, 8), dpi = 100, subplot_kw={"projection": ccrs.PlateCarree()})
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.map_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Initialisation de la carte
        self.initialize_map()

        # Gestion des points sélectionnés par l’utilisateur
        p.points = []
        self.point_selection_enabled = False

        # Boutons d'action
        self.btn_stop_selection = tk.Button(self, text="Arrêter Sélection", font=("Arial", 14), bg="red", fg="white", command=self.stop_selection)
        self.btn_reset = tk.Button(self, text="Réinitialiser", font=("Arial", 14), bg="orange", fg="white", command=self.reset_points)
        self.btn_execute = tk.Button(self, text="Lancer le Routage", font=("Arial", 14), bg="darkgreen", fg="white", command=self.execute_routing, state=tk.DISABLED)
        self.btn_execute.pack(side=tk.TOP, anchor="ne", padx=10, pady=10)

        # Bind des événements
        self.map_frame.bind("<Configure>", self.resize_canvas)

        
    def init_map(self):
        """Initialisation de la carte"""
        self.ax.set_extent(p.loc_nav, crs=ccrs.PlateCarree())
        self.ax.add_feature(cfeature.COASTLINE.with_scale("10m"), linewidth=1)
        self.ax.add_feature(cfeature.BORDERS.with_scale("10m"), linestyle=":")
        self.ax.add_feature(cfeature.LAND, facecolor="lightgray")
        self.ax.add_feature(cfeature.OCEAN, facecolor="lightblue")
        self.canvas.draw_idle()
        
    def create_menu(self):
        menu_bar = Menu(self.controller.root)
        self.controller.root.config(menu=menu_bar)

        navigation_menu = Menu(menu_bar, tearoff=0)
        navigation_menu.add_command(label="Accueil", command=lambda: self.controller.show_frame("AccueilPage"))
        menu_bar.add_cascade(label="Navigation", menu=navigation_menu)
        
        actions_menu = Menu(menu_bar, tearoff=0)
        actions_menu.add_command(label="Sélectionner Points", command=self.enable_point_selection)
        actions_menu.add_command(label="Lancer Routage", command=self.execute_routing)
        menu_bar.add_cascade(label="Actions", menu=actions_menu)
        
        menu_bar.add_cascade(label="Paramètres", command=self.open_param_window)
        
    def open_param_window(self):
        param_window = Toplevel(self.controller.root)
        param_window.title("Modifier les paramètres")
        param_window.geometry("500x700")
        
        params = {
            "pas_temporel": p.pas_temporel,
            "pas_angle": p.pas_angle,
            "heure_initiale": p.heure_initiale,
            "date_initiale": p.date_initiale,
            "tolerance": p.tolerance,
            "rayon_elemination": p.rayon_elemination,
            "skip": p.skip,
            "skip_vect_vent": p.skip_vect_vent,
            "tolerance_arrivée": p.tolerance_arrivée,
            "land_contact": p.land_contact,
            "enregistrement": p.enregistrement,
            "live": p.live,
            "print_données": p.print_données,
            "data_route": p.data_route,
            "enveloppe": p.enveloppe
        }
        
        self.entries = {}
        row = 0
        for param, value in params.items():
            Label(param_window, text=param, font=("Arial", 16)).grid(row=row, column=0, padx=20, pady=10, sticky='w')
            
            if isinstance(value, bool):
                var = BooleanVar(value=value)
                chk = Checkbutton(param_window, variable=var, font=("Arial", 16), padx=20, pady=10, highlightthickness=5)
                chk.grid(row=row, column=1, padx=20, pady=10)
                self.entries[param] = var
            else:
                frame = Frame(param_window)
                frame.grid(row=row, column=1, padx=10, pady=10)
                btn_minus = Button(frame, text="-", font=("Arial", 14), command=lambda p=param: self.adjust_param(p, -0.1))
                btn_minus.pack(side=tk.LEFT)
                entry = Entry(frame, font=("Arial", 16), width=8)
                entry.insert(0, str(value))
                entry.pack(side=tk.LEFT)
                btn_plus = Button(frame, text="+", font=("Arial", 14), command=lambda p=param: self.adjust_param(p, 0.1))
                btn_plus.pack(side=tk.LEFT)
                self.entries[param] = entry
            
            row += 1
        
        Button(param_window, text="Enregistrer", font=("Arial", 16), command=self.save_params).grid(row=row, columnspan=2, pady=20)
    
    def adjust_param(self, param, delta):
        entry = self.entries[param]
        try:
            new_value = float(entry.get()) + delta
            entry.delete(0, tk.END)
            entry.insert(0, str(new_value))
        except ValueError:
            pass
    
    def save_params(self):
        for param, widget in self.entries.items():
            new_value = widget.get() if isinstance(widget, Entry) else widget.get()
            setattr(p, param, type(getattr(p, param))(new_value))      
        
    def stop_selection(self):
        self.point_selection_enabled = False
        self.btn_stop_selection.pack_forget()
        self.btn_reset.pack_forget()
        self.update_routage_button()
    
    def reset_points(self):
        p.points = []
        self.ax.clear()
        self.initialize_map()
        self.update_routage_button()
        print("Tous les points ont été réinitialisés.")

    def enable_point_selection(self):
        self.point_selection_enabled = True
        self.canvas.get_tk_widget().bind("<Button-1>", self.on_click)
        self.btn_stop_selection.pack(side=tk.TOP, anchor="ne", padx=10, pady=10)
        self.btn_reset.pack(side=tk.TOP, anchor="ne", padx=10, pady=10)

    def initialize_map(self):
        """Initialise la carte avec Cartopy."""
        self.ax.set_extent(p.loc_nav, crs=ccrs.PlateCarree())
        self.ax.add_feature(cfeature.COASTLINE.with_scale("10m"), linewidth=1)
        self.ax.add_feature(cfeature.BORDERS.with_scale("10m"), linestyle=":")
        self.ax.add_feature(cfeature.LAND, facecolor="lightgray")
        self.ax.add_feature(cfeature.OCEAN, facecolor="lightblue")
        self.canvas.draw_idle()
    
    def resize_canvas(self, event):
        """Redimensionne la carte en fonction de la fenêtre."""
        width, height = event.width, event.height
        self.fig.set_size_inches(width / self.canvas.figure.dpi, height / self.canvas.figure.dpi, forward=True)
        self.canvas.draw_idle()

    def stop_routing(self):
        """Arrête le routage et réinitialise la position initiale."""
        print("Arrêt du routage et retour à la position initiale.")
        p.points = []
        self.ax.clear()
        self.initialize_map()
        self.canvas.draw_idle()    
    
    def on_click(self, event):
        if not self.point_selection_enabled:
            return
        
        x, y = self.ax.transData.inverted().transform((event.x, self.canvas.get_tk_widget().winfo_height() - event.y))
        
        p.points.append((y, x))
        print(f"Point sélectionné : {y:.2f}N, {x:.2f}E")
        
        color = "green" if len(p.points) == 1 else "red" if len(p.points) == 2 else "black"
        self.ax.scatter(x, y, color=color, marker="x", s=100, transform=ccrs.PlateCarree())
        self.canvas.draw_idle()
        self.update_routage_button()
    
    def update_routage_button(self):
        if len(p.points) >= 2:
            self.btn_execute.config(state=tk.NORMAL, bg="lightgreen")
        else:
            self.btn_execute.config(state=tk.DISABLED, bg="darkgreen")   

    def execute_routing(self):
        """Exécute le routage et met à jour l'affichage dans Tkinter."""
        if len(p.points) < 2:
            print("Veuillez sélectionner au moins deux points pour exécuter le routage.")
            return

        print("Lancement du routage...")
        self.controller.root.after(100, self.run_routing) 
        
    def run_routing(self):
        """Exécute le routage en arrière-plan sans bloquer Tkinter"""
        rc.itere_jusqua_dans_enveloppe_tk(p.points, self.ax, self.canvas)
        self.canvas.draw_idle()
        self.controller.root.update_idletasks()
               

        
if __name__ == "__main__":
    root = tk.Tk()
    app = RoutageApp(root)
    root.mainloop()
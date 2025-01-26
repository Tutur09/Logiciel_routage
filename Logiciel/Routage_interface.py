import tkinter as tk
from tkinter import Menu
from tkinter import Toplevel
from tkinterweb import HtmlFrame  
import folium
import Routage_Paramètres as p

import os

def generate_map():
    map_center = [48.8566, 2.3522]  # Coordonnées de Paris
    my_map = folium.Map(location=map_center, zoom_start=12)

    # Ajouter un marqueur
    folium.Marker(location=map_center, popup="Paris, France").add_to(my_map)

    # Déterminer un chemin absolu pour sauvegarder la carte
    map_file = os.path.join(os.getcwd(), "map.html")  # Chemin complet vers le fichier
    my_map.save(map_file)

    return map_file


# Fenêtre de visualisation de la carte
def open_map_window():
    map_file = generate_map()

    map_window = Toplevel()
    map_window.title("Carte Interactive")
    map_window.geometry("800x600")

    # Intégrer la carte HTML dans Tkinter
    frame = HtmlFrame(map_window)
    frame.load_file(map_file)
    frame.pack(fill="both", expand=True)

# Fonction de base inchangée
def on_button_click(button_name):
    print(f"Button '{button_name}' clicked!")

def save_settings(entries, checkboxes):
    # Sauvegarder les entrées
    p.pas_temporel = float(entries['Pas Temporel'].get())
    p.pas_angle = int(entries['Pas Angle'].get())
    p.heure_initiale = int(entries['Heure Initiale'].get())
    p.date_initiale = entries['Date Initiale (MMJJ)'].get()
    p.tolerance = float(entries['Tolérance'].get())
    p.rayon_elemination = float(entries['Rayon élimination'].get())
    p.skip = int(entries['Skip'].get())
    p.skip_vect_vent = int(entries['Skip vect vent'].get())
    p.tolerance_arrivée = float(entries['Tolérance Arrivée'].get())

    # Sauvegarder les cases à cocher
    p.land_contact = checkboxes['Land Contact'].get()
    p.enregistrement = checkboxes['Enregistrement'].get()
    p.live = checkboxes['Live'].get()
    p.print_données = checkboxes['Print Données'].get()
    p.data_route = checkboxes['Data Route'].get()
    p.enveloppe = checkboxes['Enveloppe'].get()

    print("Paramètres sauvegardés avec succès.")

def open_settings_window():
    settings_window = tk.Toplevel()
    settings_window.title("Paramètres")
    settings_window.geometry("400x400")

    # Créer une zone avec barre de défilement
    canvas = tk.Canvas(settings_window)
    scrollbar = tk.Scrollbar(settings_window, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    entries = {}
    checkboxes = {}

    # Paramètres modifiables
    tk.Label(scrollable_frame, text="Paramètres", font=("Arial", 14)).pack(pady=10)

    for label, default in [
        ("Pas Temporel", p.pas_temporel),
        ("Pas Angle", p.pas_angle),
        ("Heure Initiale", p.heure_initiale),
        ("Date Initiale (MMJJ)", p.date_initiale),
        ("Tolérance", p.tolerance),
        ("Rayon élimination", p.rayon_elemination),
        ("Skip", p.skip),
        ("Skip vect vent", p.skip_vect_vent),
        ("Tolérance Arrivée", p.tolerance_arrivée)
    ]:
        tk.Label(scrollable_frame, text=label).pack(anchor="w", padx=10)
        entry = tk.Entry(scrollable_frame)
        entry.insert(0, str(default))
        entry.pack(fill="x", padx=10, pady=5)
        entries[label] = entry

    # Cases à cocher
    for label, default in [
        ("Land Contact", p.land_contact),
        ("Enregistrement", p.enregistrement),
        ("Live", p.live),
        ("Print Données", p.print_données),
        ("Data Route", p.data_route),
        ("Enveloppe", p.enveloppe)
    ]:
        var = tk.BooleanVar(value=default)
        checkbutton = tk.Checkbutton(scrollable_frame, text=label, variable=var)
        checkbutton.pack(anchor="w", padx=10)
        checkboxes[label] = var

    tk.Button(scrollable_frame, text="Enregistrer", command=lambda: save_settings(entries, checkboxes)).pack(pady=10)

def create_main_window():
    # Créer la fenêtre principale
    window = tk.Tk()
    window.title("Logiciel de Routage")
    window.geometry("800x600")

    # Créer une barre de menu
    menu_bar = Menu(window)

    # Ajouter un menu "Fichier"
    file_menu = Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="Nouveau", command=lambda: on_button_click("Nouveau"))
    file_menu.add_command(label="Ouvrir", command=lambda: on_button_click("Ouvrir"))
    file_menu.add_command(label="Sauvegarder", command=lambda: on_button_click("Sauvegarder"))
    file_menu.add_separator()
    file_menu.add_command(label="Quitter", command=window.quit)
    menu_bar.add_cascade(label="Fichier", menu=file_menu)

    # Ajouter un menu "Paramètres"
    settings_menu = Menu(menu_bar, tearoff=0)
    settings_menu.add_command(label="Options de Routage", command=open_settings_window)
    settings_menu.add_command(label="Configuration", command=lambda: on_button_click("Configuration"))
    menu_bar.add_cascade(label="Paramètres", menu=settings_menu)

    # Ajouter un menu "Carte"
    map_menu = Menu(menu_bar, tearoff=0)
    map_menu.add_command(label="Afficher la Carte", command=open_map_window)
    menu_bar.add_cascade(label="Carte", menu=map_menu)

    # Ajouter un menu "Aide"
    help_menu = Menu(menu_bar, tearoff=0)
    help_menu.add_command(label="Documentation", command=lambda: on_button_click("Documentation"))
    help_menu.add_command(label="À propos", command=lambda: on_button_click("À propos"))
    menu_bar.add_cascade(label="Aide", menu=help_menu)

    # Configurer la fenêtre pour utiliser la barre de menu
    window.config(menu=menu_bar)

    # Ajouter une zone principale pour les widgets
    main_frame = tk.Frame(window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Exemple de widgets dans la zone principale
    tk.Label(main_frame, text="Bienvenue dans le logiciel de routage!", font=("Arial", 16)).pack(pady=20)
    tk.Button(main_frame, text="Commencer le Routage", command=lambda: on_button_click("Commencer le Routage")).pack(pady=10)

    return window

if __name__ == "__main__":
    app_window = create_main_window()
    app_window.mainloop()

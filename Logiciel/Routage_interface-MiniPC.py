import tkinter as tk
from tkinter import Menu, Toplevel
import Routage_Paramètres as p
import Routage_calcul as rc

class RoutageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Logiciel de Routage")
        self.root.geometry("900x600")

        self.create_menu()
        self.create_canvas()
        self.create_controls()

    def create_menu(self):
        menu_bar = Menu(self.root)
        
        file_menu = Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Quitter", command=self.root.quit)
        menu_bar.add_cascade(label="Fichier", menu=file_menu)

        settings_menu = Menu(menu_bar, tearoff=0)
        settings_menu.add_command(label="Paramètres", command=self.open_settings_window)
        menu_bar.add_cascade(label="Paramètres", menu=settings_menu)

        self.root.config(menu=menu_bar)

    def create_canvas(self):
        self.canvas = tk.Canvas(self.root, bg="lightblue", width=800, height=500)
        self.canvas.pack(pady=10)
        
        # Points de départ et d'arrivée (Exemple arbitraire)
        self.start = (100, 400)  # x, y
        self.end = (700, 100)  # x, y
        
        self.canvas.create_oval(self.start[0]-5, self.start[1]-5, self.start[0]+5, self.start[1]+5, fill='green')
        self.canvas.create_oval(self.end[0]-5, self.end[1]-5, self.end[0]+5, self.end[1]+5, fill='red')

    def create_controls(self):
        btn = tk.Button(self.root, text="Lancer le routage", command=self.run_routing)
        btn.pack()

    def run_routing(self):
        # Simulation de la route entre start et end (Exemple simple)
        self.canvas.create_line(self.start[0], self.start[1], self.end[0], self.end[1], fill='black', width=2)

    def open_settings_window(self):
        settings_window = Toplevel(self.root)
        settings_window.title("Paramètres")
        settings_window.geometry("300x300")

        tk.Label(settings_window, text="Pas Temporel").pack()
        entry = tk.Entry(settings_window)
        entry.insert(0, str(p.pas_temporel))
        entry.pack()

if __name__ == "__main__":
    root = tk.Tk()
    app = RoutageApp(root)
    root.mainloop()

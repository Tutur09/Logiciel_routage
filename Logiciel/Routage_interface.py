from PyQt5.QtWidgets import QMainWindow, QApplication, QVBoxLayout
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from interface import Ui_MainWindow  # Interface générée par Qt Designer

class RoutageApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)  # Charge l'interface Qt Designer

        # 🔹 Ajouter la carte Matplotlib dans widgetRoutage
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)

        # 🔹 S'assurer que widgetRoutage utilise un layout
        layout = QVBoxLayout(self.widgetRoutage)
        layout.setContentsMargins(0, 0, 0, 0)  # Supprime les marges
        layout.addWidget(self.canvas)

        # 🔹 Initialisation de la carte et des événements
        self.init_map()
        self.canvas.mpl_connect("scroll_event", self.zoom)
        self.canvas.mpl_connect("button_press_event", self.start_drag)
        self.canvas.mpl_connect("motion_notify_event", self.drag)
        self.canvas.mpl_connect("button_release_event", self.stop_drag)

        # 🔹 Variables pour le déplacement
        self.dragging = False
        self.prev_mouse_pos = None

    def init_map(self):
        """Initialise la carte Cartopy sans marges"""
        self.ax = self.figure.add_subplot(111, projection=ccrs.PlateCarree())
        self.ax.set_extent([-180, 180, -90, 90], crs=ccrs.PlateCarree())

        # 🔹 Supprimer les marges Matplotlib
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.ax.set_position([0, 0, 1, 1])

        # 🔹 Supprimer les axes
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_frame_on(False)

        # 🔹 Ajouter les éléments géographiques
        self.ax.add_feature(cfeature.COASTLINE)
        self.ax.add_feature(cfeature.BORDERS, linestyle=":")
        self.ax.add_feature(cfeature.LAND, facecolor="lightgray")
        self.ax.add_feature(cfeature.OCEAN, facecolor="lightblue")

        self.canvas.draw()

    def zoom(self, event):
        """Zoom avec la molette"""
        zoom_factor = 1.2 if event.step > 0 else 0.8  # Zoom avant/arrière
        xlim, ylim = self.ax.get_xlim(), self.ax.get_ylim()

        self.ax.set_xlim([
            event.xdata - (event.xdata - xlim[0]) * zoom_factor,
            event.xdata + (xlim[1] - event.xdata) * zoom_factor
        ])
        self.ax.set_ylim([
            event.ydata - (event.ydata - ylim[0]) * zoom_factor,
            event.ydata + (ylim[1] - event.ydata) * zoom_factor
        ])
        self.canvas.draw()

    def start_drag(self, event):
        """Début du déplacement avec le clic gauche"""
        if event.button == 1:
            self.dragging = True
            self.prev_mouse_pos = (event.xdata, event.ydata)

    def drag(self, event):
        """Déplacement de la carte avec le clic gauche maintenu"""
        if self.dragging and event.xdata is not None and event.ydata is not None:
            dx = self.prev_mouse_pos[0] - event.xdata
            dy = self.prev_mouse_pos[1] - event.ydata
            xlim, ylim = self.ax.get_xlim(), self.ax.get_ylim()

            self.ax.set_xlim(xlim[0] + dx, xlim[1] + dx)
            self.ax.set_ylim(ylim[0] + dy, ylim[1] + dy)

            self.prev_mouse_pos = (event.xdata, event.ydata)
            self.canvas.draw()

    def stop_drag(self, event):
        """Arrêt du déplacement quand le clic gauche est relâché"""
        if event.button == 1:
            self.dragging = False

if __name__ == "__main__":
    app = QApplication([])
    window = RoutageApp()
    window.show()
    app.exec_()

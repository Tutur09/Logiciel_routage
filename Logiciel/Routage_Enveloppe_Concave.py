import numpy as np
from scipy.spatial import Delaunay
import matplotlib.pyplot as plt
from collections import defaultdict
import random

def calculate_angles(p1, p2, p3):
    # Calcul des longueurs de chaque côté
    a = np.linalg.norm(p2 - p3)  # opposé à p1
    b = np.linalg.norm(p1 - p3)  # opposé à p2
    c = np.linalg.norm(p1 - p2)  # opposé à p3

    # Vérification pour éviter une division par zéro
    if b * c == 0 or a * c == 0:
        return 0, 0  # Retourne un angle nul si un côté est nul

    # Calcul des angles en radians
    angle_p1 = np.arccos(np.clip((b**2 + c**2 - a**2) / (2 * b * c), -1, 1))
    angle_p2 = np.arccos(np.clip((a**2 + c**2 - b**2) / (2 * a * c), -1, 1))

    # Conversion en degrés
    return np.degrees(angle_p1), np.degrees(angle_p2)


def find_boundary_edges(triangles):
    """
    Identify edges that belong to only one triangle (boundary edges).
    """
    edge_count = defaultdict(int)
    for tri in triangles:
        edges = [(tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])]
        for edge in edges:
            edge_count[tuple(sorted(edge))] += 1
    return {edge for edge, count in edge_count.items() if count == 1}

def filter_triangles_on_edge(points, triangles, min_angle=20, max_angle=60):
    """
    Remove triangles on the edge with boundary angles not in [min_angle, max_angle].
    """
    boundary_edges = find_boundary_edges(triangles)
    retained_triangles = []
    for tri_indices in triangles:
        edges = [(tri_indices[0], tri_indices[1]),
                 (tri_indices[1], tri_indices[2]),
                 (tri_indices[2], tri_indices[0])]

        is_removed = False
        for edge in edges:
            if tuple(sorted(edge)) in boundary_edges:
                # Calculate the angle opposite to the boundary edge
                opposite_point = list(set(tri_indices) - set(edge))[0]
                p1, p2, p3 = points[edge[0]], points[edge[1]], points[opposite_point]
                angle1, angle2 = calculate_angles(p1, p2, p3)
                # Si l'angle n'est pas dans l'intervalle [min_angle, max_angle], on retire le triangle
                if (angle1 < min_angle and angle2 < max_angle) or (angle2 < min_angle and angle1 < max_angle):
                
                    is_removed = True
                    break
        if not is_removed:
            retained_triangles.append(tri_indices)
    return np.array(retained_triangles)

def get_outer_shell(points, filtered_triangles):
    """
    Get the outer shell (boundary edges) of the remaining triangles.
    Returns the edges as a list of tuples: [((x1,y1),(x2,y2)), ...]
    """
    edge_count = defaultdict(int)
    for tri_indices in filtered_triangles:
        edges = [(tri_indices[0], tri_indices[1]),
                 (tri_indices[1], tri_indices[2]),
                 (tri_indices[2], tri_indices[0])]
        for edge in edges:
            edge_count[tuple(sorted(edge))] += 1

    boundary_edges = [edge for edge, count in edge_count.items() if count == 1]

    # Convertir chaque edge en ((x1, y1), (x2, y2)) plutôt que (array([...]), array([...]))
    boundary_coords = []
    for e in boundary_edges:
        p1 = points[e[0]]
        p2 = points[e[1]]
        # Convertir l'array NumPy en tuple
        p1_tuple = (float(p1[0]), float(p1[1]))
        p2_tuple = (float(p2[0]), float(p2[1]))
        boundary_coords.append(p1_tuple)
        boundary_coords.append(p2_tuple)

    return boundary_coords

def order_boundary_points(boundary_coords):
    """
    Trie logiquement les points de l'enveloppe extérieure pour former une boucle ordonnée.
    """
    edge_map = defaultdict(list)
    for i in range(0, len(boundary_coords), 2):
        p1 = boundary_coords[i]
        p2 = boundary_coords[i + 1]
        edge_map[p1].append(p2)
        edge_map[p2].append(p1)

    start_point = min(edge_map.keys(), key=lambda p: (p[0], p[1]))

    ordered_points = [start_point]
    current_point = start_point
    previous_point = None

    while True:
        next_points = edge_map[current_point]
        if len(next_points) == 1:  # Si un seul voisin, éviter l'erreur
            next_point = next_points[0]
        else:
            next_point = next_points[0] if next_points[0] != previous_point else next_points[1]

        if next_point == start_point:
            break

        ordered_points.append(next_point)
        previous_point, current_point = current_point, next_point

    return ordered_points

def enveloppe_concave(points):
    tri = Delaunay(points)
    filtered_triangles = tri.simplices
    stable = False
    triangle = len(filtered_triangles)
    outer_shell = []  # Initialisation pour éviter une erreur

    while not stable:
        filtered_triangles = filter_triangles_on_edge(points, filtered_triangles)
        triangle_new = len(filtered_triangles)
        if triangle_new == triangle:
            stable = True
        else:
            triangle = triangle_new

        if len(filtered_triangles) > 0:
            outer_shell = get_outer_shell(points, filtered_triangles)

    return order_boundary_points(outer_shell) if outer_shell else []

def concave_random(n):
    points = [(random.randint(0, 100), random.randint(0, 100)) for _ in range(n)]
    env_concave = enveloppe_concave(np.array(points))
    env_concave.append(env_concave[0])
    fig, ax = plt.subplots()
    ax.plot(*zip(points), marker = 'o', color = 'b')
    ax.plot(*zip(*env_concave), marker = 'o', color = 'r')
    plt.show()

def plot_triangles(points, triangles, concave_hull=None):
    """
    Affiche la triangulation de Delaunay et l'enveloppe concave (si fournie).
    """
    fig, ax = plt.subplots(figsize=(8, 6))

    # Tracé des triangles
    for tri in triangles:
        pts = points[tri]  # S'assurer que points est bien un np.array
        polygon = plt.Polygon(pts, edgecolor='gray', fill=None, linewidth=1)
        ax.add_patch(polygon)

    # Tracé des points initiaux
    ax.scatter(points[:, 0], points[:, 1], color='blue', label="Points")

    # Tracé de l'enveloppe concave (si fournie)
    if concave_hull:
        concave_hull.append(concave_hull[0])  # Ferme la boucle si elle existe
        ax.plot(*zip(*concave_hull), marker='o', linestyle='-', color='red', linewidth=2, label="Enveloppe concave")

    ax.legend()
    ax.set_title("Triangulation de Delaunay et enveloppe concave")
    plt.show()

if __name__ == '__main__':
    points = np.array([(random.randint(0, 100), random.randint(0, 100)) for _ in range(100)])  # Convertir en np.array
    triangulation = Delaunay(points)
    plot_triangles(points, triangulation.simplices, enveloppe_concave(points))


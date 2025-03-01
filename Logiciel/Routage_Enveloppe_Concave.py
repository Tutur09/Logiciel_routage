import numpy as np
from scipy.spatial import Delaunay
import matplotlib.pyplot as plt
from collections import defaultdict

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

if __name__ == '__main__':
    points = [(46.012422974556095, -5.549347066718002), (46.00973725673662, -5.477764067156145), (46.00127975207347, -5.414777825334667), (46.00125201132839, -5.335018226975538), (46.003786333835805, -5.282712168887242), (46.006496461779506, -5.2022480192069604), (46.00647401032872, -5.130493790139045), (46.000961693235205, -5.0468302649814225), (46.00196243846558, -4.992227236461752), (46.01336995986486, -4.923617011461549), (46.0387633199283, -4.869041799871829), (46.06827396009881, -4.799459785691071), (46.115771812241874, -4.769769338113613), (46.1569692746202, -4.716575087588975), (46.19942164386077, -4.6804547065525375), (46.22686632596371, -4.632548014176481), (46.25311655414511, -4.583524401269348), (46.29582477801836, -4.537870294896847), (46.33493480957401, -4.485225510883122), (46.369216885664166, -4.448641792313269), (46.40913994211517, -4.397345592993551), (46.44770755575648, -4.353664451460494), (46.487700517632646, -4.251077314156284), (46.5363179957164, -4.206508353814827), (46.5563937011389, -4.144221735116406), (46.579971856094616, -4.055736973560463), (46.600711569611676, -3.9970518231438064), (46.63118205222566, -3.940818962050987), (46.66493990368807, -3.895174376464921), (46.68584842870148, -3.8490488045529023), (46.72111672104385, -3.8086246511404704), (46.76738406602876, -3.7594777810772806), (46.8021413634688, -3.715710396208164), (46.838922520499914, -3.68099444439479), (46.87146944327821, -3.6311263340555), (46.91142516717523, -3.5957372234973524), (46.95091216675025, -3.5457129755855443), (47.00455263313037, -3.492231794684204), (47.056372969813836, -3.4496126177027664), (47.0977188901994, -3.409606414767522), (47.15430726434713, -3.3689503525517326), (47.19803239199462, -3.3372964935374982), (47.237167552207104, -3.303320043970917), (47.317864655481706, -3.2509277846574958), (47.379023153346736, -3.2341153232977424), (47.43668443196822, -3.1823179437434885), (47.489412469640605, -3.1830359897855343), (47.54428288009455, -3.215250186923842), (47.570342041724516, -3.2921118550091717), (47.627286503151815, -3.293133595526968), (47.66278879655464, -3.334500075492278), (47.685299386199546, -3.386424575974929), (47.720382099960226, -3.4452246944407285)]#, (48.058675579234404, -3.601416876569087)]#, (48.18070480290864, -3.5244800704583144)]

    points2 = enveloppe_concave(np.array(points))

    plt.figure(figsize=(10, 8))
    plt.plot(*zip(*points), 'o', label='Points')
    plt.plot(*zip(*points2), 'r-', label='Enveloppe Concave')
    plt.show()

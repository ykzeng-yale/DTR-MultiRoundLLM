"""Pure functions extracted unchanged from Reasoning Gym at a pinned revision.

Upstream: open-thought/reasoning-gym
Revision: 49b07130b3fcd12f2d064bba7c43869543a0e7e7
Source: reasoning_gym/algorithmic/graph_color.py
License: Apache-2.0; see REASONING_GYM_LICENSE and the extraction manifest.
Only these three functions are included; the upstream package is not imported.
"""

def generate_random_graph(rng, num_vertices, edge_probability=0.3):
    """
    Generate an undirected random graph.

    Args:
        num_vertices (int): The number of vertices.
        edge_probability (float): Probability for an edge to exist between any two vertices.

    Returns:
        tuple: (vertices, edges)
            - vertices: A list of vertex identifiers (0 to num_vertices-1).
            - edges: A list of tuples (u, v) representing undirected edges.
    """
    vertices = list(range(num_vertices))
    edges = []
    for i in range(num_vertices):
        for j in range(i + 1, num_vertices):
            if rng.random() < edge_probability:
                edges.append((i, j))
    return vertices, edges


def verify_graph_coloring_solution(puzzle, coloring):
    """
    Verifies that a candidate coloring is a valid solution to the graph coloring puzzle.

    Args:
        puzzle (dict): The puzzle specification containing 'vertices', 'edges', and 'color_options'.
        coloring (dict): A dictionary mapping each vertex to a color. The keys can be integers or strings.

    Returns:
        tuple: (is_valid, message) where is_valid is a boolean and message is a string explanation.
    """
    vertices = puzzle["vertices"]
    edges = puzzle["edges"]
    allowed_colors = set(puzzle["color_options"])

    # Helper function to get a vertex's color regardless of key type.
    def get_color(vertex):
        # If the key matches as-is, return it.
        if vertex in coloring:
            return coloring[vertex]
        # If the vertex is an integer and its string form is a key, return that.
        elif isinstance(vertex, int) and str(vertex) in coloring:
            return coloring[str(vertex)]
        # If the vertex is a string, try to convert it to int and look it up.
        elif isinstance(vertex, str):
            try:
                vertex_int = int(vertex)
                if vertex_int in coloring:
                    return coloring[vertex_int]
            except ValueError:
                pass
        # If no matching key is found, signal an error.
        raise KeyError(f"Vertex {vertex} has not been assigned a color.")

    # Check that every vertex has been assigned a color.
    for vertex in vertices:
        try:
            get_color(vertex)
        except KeyError:
            return False, f"Not all vertices have been assigned a color (missing vertex {vertex})."

    # Check that only allowed colors are used.
    for vertex in vertices:
        try:
            color = get_color(vertex)
        except KeyError as e:
            return False, str(e)
        if color not in allowed_colors:
            return False, f"Vertex {vertex} uses an invalid color: {color}."

    # Ensure that adjacent vertices do not share the same color.
    for u, v in edges:
        try:
            color_u = get_color(u)
            color_v = get_color(v)
        except KeyError as e:
            return False, str(e)
        if color_u == color_v:
            return False, f"Adjacent vertices {u} and {v} both have color {color_u}."

    return True, "The coloring is valid."


def greedy_graph_coloring(puzzle):
    """
    Attempts to color the graph using a simple greedy algorithm.
    (Note: This may fail if the graph requires more than the given number of colors.)

    Args:
        puzzle (dict): The puzzle specification.

    Returns:
        dict or None: A dictionary mapping vertices to colors if successful; otherwise, None.
    """
    vertices = puzzle["vertices"]
    edges = puzzle["edges"]
    color_options = puzzle["color_options"]

    # Build an adjacency list for each vertex.
    adjacency = {v: set() for v in vertices}
    for u, v in edges:
        adjacency[u].add(v)
        adjacency[v].add(u)

    coloring = {}
    for v in vertices:
        # Find colors already used by neighbors.
        neighbor_colors = {coloring.get(neighbor) for neighbor in adjacency[v] if neighbor in coloring}
        # Pick the first available color not used by any neighbor.
        available = [color for color in color_options if color not in neighbor_colors]
        if not available:
            return None  # Failed to color with the given number of colors.
        coloring[v] = available[0]
    return coloring

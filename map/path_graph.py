# ==============================
# PATH GRAPH (Single Source of Truth for Path)
# ==============================
class PathGraph:
    def __init__(self):
        self.nodes = set()  # set of (x, y) tuples
        self.edges = set()  # set of frozenset({(x,y), (x,y)}) for adjacent pairs
        self.start = None   # (x, y) start position
        self.end = None     # (x, y) end position
        self._ordered_path = []  # cached ordered path from start to end

    def add_node(self, pos):
        """Add a path node at position (x, y)."""
        self.nodes.add(pos)
        self._ordered_path = []  # invalidate cache

    def add_edge(self, pos1, pos2):
        """Add an edge between two positions."""
        # Allow any edge - the path generator knows what connections are valid
        self.edges.add(frozenset([pos1, pos2]))
        self._ordered_path = []  # invalidate cache

    def set_start(self, pos):
        """Set the start position."""
        self.start = pos
        if pos not in self.nodes:
            self.add_node(pos)
        self._ordered_path = []  # invalidate cache

    def set_end(self, pos):
        """Set the end position."""
        self.end = pos
        if pos not in self.nodes:
            self.add_node(pos)
        self._ordered_path = []  # invalidate cache

    def compute_ordered_path(self):
        """Compute ordered path from start to end using BFS."""
        if not self.start or not self.end:
            return []

        if self._ordered_path:  # return cached path
            return self._ordered_path

        # BFS to find path from start to end
        from collections import deque
        queue = deque([self.start])
        came_from = {self.start: None}

        while queue:
            current = queue.popleft()
            if current == self.end:
                break

            # Find neighbors via edges
            for edge in self.edges:
                if current in edge:
                    neighbor = next(p for p in edge if p != current)
                    if neighbor not in came_from:
                        came_from[neighbor] = current
                        queue.append(neighbor)

        # Reconstruct path
        if self.end not in came_from:
            return []  # no path found

        path = []
        current = self.end
        while current is not None:
            path.append(current)
            current = came_from[current]
        path.reverse()

        self._ordered_path = path
        return path

    def get_ordered_path(self):
        """Get the ordered path from start to end."""
        return self.compute_ordered_path()
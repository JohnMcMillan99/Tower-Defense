import random

class PathGenerator:
    def __init__(self, height, width):
        self.height = height
        self.width = width
        self.path = []

    def cell_is_free(self, x, y):
        return (x, y) not in self.path

    def generate_path(self):
        self.path = []
        y = self.height // 2
        x = 0
        # For smaller grids, be more flexible with movement constraints
        min_margin = max(1, self.height // 6)  # Adaptive margin
        while x < self.width:
            self.path.append((x, y))
            valid_move = False
            attempts = 0
            while not valid_move and attempts < 10:  # Prevent infinite loops
                move = random.randint(0, 2)
                if move == 0 or x % 2 == 0 or x > (self.width - 2):
                    x += 1
                    valid_move = True
                elif move == 1 and self.cell_is_free(x, y + 1) and y < (self.height - min_margin):
                    y += 1
                    valid_move = True
                elif move == 2 and self.cell_is_free(x, y - 1) and y > min_margin:
                    y -= 1
                    valid_move = True
                attempts += 1
            if not valid_move:
                # If stuck, just move right
                x += 1
        return self.path

    def generate_loop(self):
        # For smaller grids, be more lenient with loop generation
        min_margin = min(2, self.width // 4, self.height // 4)  # Adaptive margin
        for i in range(len(self.path) - 1):  # Need i+1 to exist
            px, py = self.path[i]
            next_x, next_y = self.path[i+1]
            if px > min_margin and px < self.width - min_margin - 1 and py > min_margin and py < self.height - min_margin - 1:
                # Create a simple detour: go right, then back to next cell
                detour_cells = []
                # Go right from current cell
                detour_x = px + 1
                detour_y = py
                if self.cell_is_free(detour_x, detour_y):
                    detour_cells.append((detour_x, detour_y))
                    # Try to connect back to next cell
                    if abs(detour_x - next_x) + abs(detour_y - next_y) == 1:
                        # Direct connection
                        pass
                    elif detour_y != next_y and self.cell_is_free(detour_x, next_y):
                        # Go to same x as detour, y as next
                        detour_cells.append((detour_x, next_y))
                    elif detour_x != next_x and self.cell_is_free(next_x, detour_y):
                        # Go to same y as detour, x as next
                        detour_cells.append((next_x, detour_y))

                    if detour_cells and all(self.cell_is_free(cx, cy) for cx, cy in detour_cells):
                        # Make sure the last detour cell connects to next cell
                        last_dx, last_dy = detour_cells[-1]
                        if abs(last_dx - next_x) + abs(last_dy - next_y) == 1:
                            self.path[i+1:i+1] = detour_cells
                            return True
        return False
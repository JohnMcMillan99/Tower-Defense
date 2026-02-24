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
        for i in range(len(self.path)):
            px, py = self.path[i]
            if px > min_margin and px < self.width - min_margin - 1 and py > min_margin and py < self.height - min_margin - 1:
                # Try smaller loops for smaller grids
                loop_size = min(2, self.width // 5, self.height // 5)
                cells_to_check = []
                for dy in range(loop_size + 1):
                    for dx in range(loop_size + 1):
                        if dx == 0 and dy == 0:
                            continue  # Skip the current cell
                        cells_to_check.append((px + dx, py + dy))

                if all(self.cell_is_free(cx, cy) for cx, cy in cells_to_check):
                    self.path[i+1:i+1] = cells_to_check
                    return True
        return False
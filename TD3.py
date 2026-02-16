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
        while x < self.width:
            self.path.append((x, y))
            valid_move = False
            while not valid_move:
                move = random.randint(0, 2)
                if move == 0 or x % 2 == 0 or x > (self.width - 2):
                    x += 1
                    valid_move = True
                elif move == 1 and self.cell_is_free(x, y + 1) and y < (self.height - 3):
                    y += 1
                    valid_move = True
                elif move == 2 and self.cell_is_free(x, y - 1) and y > 2:
                    y -= 1
                    valid_move = True
        return self.path

    def generate_loop(self):
        for i in range(len(self.path)):
            px, py = self.path[i]
            if px > 2 and px < self.width - 3 and py > 2 and py < self.height - 3:
                cells_to_check = [
                    (px + 1, py), (px + 2, py),
                    (px + 2, py + 1), (px + 2, py + 2),
                    (px + 1, py + 2), (px, py + 2),
                    (px, py + 1)
                ]
                if all(self.cell_is_free(cx, cy) for cx, cy in cells_to_check):
                    self.path[i+1:i+1] = cells_to_check
                    return True
        return False
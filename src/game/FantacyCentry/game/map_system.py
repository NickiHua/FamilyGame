"""地图/网格系统"""
import pygame

TILE_SIZE = 32

# 地形类型
TERRAIN_PLAIN = "plain"
TERRAIN_FOREST = "forest"
TERRAIN_MOUNTAIN = "mountain"
TERRAIN_WATER = "water"
TERRAIN_WALL = "wall"

# 地形属性: (移动消耗, 防御加成, 闪避加成)
TERRAIN_PROPS = {
    TERRAIN_PLAIN: (1, 0, 0),
    TERRAIN_FOREST: (2, 1, 10),
    TERRAIN_MOUNTAIN: (3, 2, 15),
    TERRAIN_WATER: (99, 0, -5),
    TERRAIN_WALL: (99, 3, 0),
}

# 地形颜色(占位)
TERRAIN_COLORS = {
    TERRAIN_PLAIN: (120, 180, 80),
    TERRAIN_FOREST: (40, 100, 40),
    TERRAIN_MOUNTAIN: (140, 120, 100),
    TERRAIN_WATER: (60, 100, 180),
    TERRAIN_WALL: (80, 80, 80),
}


class Tile:
    def __init__(self, terrain=TERRAIN_PLAIN):
        self.terrain = terrain
        self.unit = None

    @property
    def move_cost(self):
        return TERRAIN_PROPS[self.terrain][0]

    @property
    def defense_bonus(self):
        return TERRAIN_PROPS[self.terrain][1]

    @property
    def evasion_bonus(self):
        return TERRAIN_PROPS[self.terrain][2]

    @property
    def passable(self):
        return self.terrain not in (TERRAIN_WATER, TERRAIN_WALL)


class MapSystem:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.tiles = []
        self.camera_x = 0
        self.camera_y = 0

    def load_map(self, map_data):
        """从地图数据加载"""
        self.width = map_data["width"]
        self.height = map_data["height"]
        self.tiles = []
        for row in range(self.height):
            tile_row = []
            for col in range(self.width):
                terrain = map_data["terrain"][row][col]
                tile_row.append(Tile(terrain))
            self.tiles.append(tile_row)

    def create_empty(self, width, height):
        """创建空地图"""
        self.width = width
        self.height = height
        self.tiles = [[Tile() for _ in range(width)] for _ in range(height)]

    def get_tile(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None

    def get_movement_range(self, x, y, move_points, flying=False):
        """BFS计算可移动范围"""
        reachable = set()
        queue = [(x, y, move_points)]
        visited = {(x, y)}

        while queue:
            cx, cy, remaining = queue.pop(0)
            reachable.add((cx, cy))

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in visited:
                    continue
                tile = self.get_tile(nx, ny)
                if tile is None:
                    continue
                cost = 1 if flying else tile.move_cost
                if not flying and not tile.passable:
                    continue
                if remaining - cost >= 0:
                    visited.add((nx, ny))
                    queue.append((nx, ny, remaining - cost))

        return reachable

    def get_attack_range(self, x, y, min_range, max_range):
        """计算攻击范围"""
        cells = set()
        for dx in range(-max_range, max_range + 1):
            for dy in range(-max_range, max_range + 1):
                dist = abs(dx) + abs(dy)
                if min_range <= dist <= max_range:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        cells.add((nx, ny))
        return cells

    def render(self, screen, camera_x=0, camera_y=0):
        """渲染地图"""
        for row in range(self.height):
            for col in range(self.width):
                tile = self.tiles[row][col]
                color = TERRAIN_COLORS.get(tile.terrain, (100, 100, 100))
                rect = pygame.Rect(
                    col * TILE_SIZE - camera_x,
                    row * TILE_SIZE - camera_y,
                    TILE_SIZE, TILE_SIZE
                )
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (50, 50, 50), rect, 1)

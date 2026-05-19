"""镜头/视口控制"""
import pygame

TILE_SIZE = 32


class Camera:
    def __init__(self, screen_width, screen_height):
        self.x = 0
        self.y = 0
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.speed = 300  # pixels per second

    def update(self, dt, keys=None):
        if keys is None:
            keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.x -= self.speed * dt
        if keys[pygame.K_RIGHT]:
            self.x += self.speed * dt
        if keys[pygame.K_UP]:
            self.y -= self.speed * dt
        if keys[pygame.K_DOWN]:
            self.y += self.speed * dt

    def clamp(self, map_width, map_height):
        max_x = map_width * TILE_SIZE - self.screen_width
        max_y = map_height * TILE_SIZE - self.screen_height
        self.x = max(0, min(self.x, max_x))
        self.y = max(0, min(self.y, max_y))

    def center_on(self, grid_x, grid_y):
        self.x = grid_x * TILE_SIZE - self.screen_width // 2
        self.y = grid_y * TILE_SIZE - self.screen_height // 2

    def screen_to_grid(self, screen_x, screen_y):
        grid_x = int((screen_x + self.x) // TILE_SIZE)
        grid_y = int((screen_y + self.y) // TILE_SIZE)
        return grid_x, grid_y

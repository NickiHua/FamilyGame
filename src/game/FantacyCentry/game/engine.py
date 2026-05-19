"""游戏主循环引擎"""
import pygame
from game.map_system import MapSystem
from game.ui import UIManager
from game.combat import CombatManager
from game.world_map import WorldMap
from game.dialogue import DialogueSystem

# 常量
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
TILE_SIZE = 32
FPS = 60

# 游戏状态
STATE_TITLE = "title"
STATE_WORLD_MAP = "world_map"
STATE_BATTLE = "battle"
STATE_DIALOGUE = "dialogue"


class GameEngine:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("幻世纪")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = STATE_TITLE

        self.map_system = MapSystem()
        self.ui = UIManager(self.screen)
        self.combat = CombatManager()
        self.world_map = WorldMap()
        self.dialogue = DialogueSystem()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.render()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                else:
                    self._dispatch_event(event)
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
                self._dispatch_event(event)

    def _dispatch_event(self, event):
        if self.state == STATE_TITLE:
            self._handle_title_event(event)
        elif self.state == STATE_WORLD_MAP:
            self.world_map.handle_event(event)
        elif self.state == STATE_BATTLE:
            self.combat.handle_event(event)
        elif self.state == STATE_DIALOGUE:
            self.dialogue.handle_event(event)

    def _handle_title_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.state = STATE_WORLD_MAP

    def update(self, dt):
        if self.state == STATE_WORLD_MAP:
            self.world_map.update(dt)
        elif self.state == STATE_BATTLE:
            self.combat.update(dt)
        elif self.state == STATE_DIALOGUE:
            self.dialogue.update(dt)

    def render(self):
        self.screen.fill((0, 0, 0))

        if self.state == STATE_TITLE:
            self.ui.render_title_screen()
        elif self.state == STATE_WORLD_MAP:
            self.world_map.render(self.screen)
        elif self.state == STATE_BATTLE:
            self.combat.render(self.screen)
            self.ui.render_battle_ui(self.combat)
        elif self.state == STATE_DIALOGUE:
            self.dialogue.render(self.screen)

        pygame.display.flip()

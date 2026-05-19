"""UI管理器"""
import pygame


class UIManager:
    def __init__(self, screen):
        self.screen = screen
        self.font = None
        self.title_font = None
        self._init_fonts()

    def _init_fonts(self):
        try:
            self.font = pygame.font.SysFont("simsun", 18)
            self.title_font = pygame.font.SysFont("simsun", 48)
        except Exception:
            self.font = pygame.font.Font(None, 18)
            self.title_font = pygame.font.Font(None, 48)

    def render_title_screen(self):
        """渲染标题画面"""
        self.screen.fill((10, 10, 30))

        # 标题
        if self.title_font:
            title = self.title_font.render("幻 世 纪", True, (255, 215, 0))
            rect = title.get_rect(center=(512, 280))
            self.screen.blit(title, rect)

        # 提示
        if self.font:
            hint = self.font.render("按 Enter 开始游戏", True, (180, 180, 180))
            rect = hint.get_rect(center=(512, 450))
            self.screen.blit(hint, rect)

    def render_battle_ui(self, combat):
        """渲染战斗UI"""
        # 回合信息
        if self.font:
            turn_text = f"第 {combat.turn} 回合  {'我方' if combat.phase == 'player' else '敌方'}行动"
            surf = self.font.render(turn_text, True, (255, 255, 255))
            self.screen.blit(surf, (10, 10))

        # 选中单位信息
        if combat.selected_unit:
            self._render_unit_info(combat.selected_unit, 10, 700)

    def _render_unit_info(self, unit, x, y):
        """渲染单位信息面板"""
        panel = pygame.Rect(x, y, 250, 60)
        pygame.draw.rect(self.screen, (20, 20, 40, 200), panel)
        pygame.draw.rect(self.screen, (200, 170, 80), panel, 1)

        if self.font:
            name = self.font.render(f"{unit.name} Lv.{unit.level}", True, (255, 220, 100))
            self.screen.blit(name, (x + 8, y + 5))

            hp_text = f"HP: {unit.hp}/{unit.max_hp}  MP: {unit.mp}/{unit.max_mp}"
            hp_surf = self.font.render(hp_text, True, (255, 255, 255))
            self.screen.blit(hp_surf, (x + 8, y + 30))

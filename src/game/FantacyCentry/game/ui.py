"""UI管理器"""
import pygame


class UIManager:
    def __init__(self, screen):
        self.screen = screen
        self.font = None
        self.title_font = None
        self.small_font = None
        self._init_fonts()

    def _init_fonts(self):
        try:
            self.font = pygame.font.SysFont("simsun", 18)
            self.title_font = pygame.font.SysFont("simsun", 52, bold=True)
            self.small_font = pygame.font.SysFont("simsun", 14)
        except Exception:
            self.font = pygame.font.Font(None, 18)
            self.title_font = pygame.font.Font(None, 52)
            self.small_font = pygame.font.Font(None, 14)

    def render_title_screen(self):
        """渲染标题画面"""
        self.screen.fill((8, 8, 25))

        # 装饰线
        pygame.draw.line(self.screen, (80, 60, 20), (200, 250), (824, 250), 1)
        pygame.draw.line(self.screen, (80, 60, 20), (200, 380), (824, 380), 1)

        # 标题
        if self.title_font:
            title = self.title_font.render("幻 世 纪", True, (255, 215, 0))
            shadow = self.title_font.render("幻 世 纪", True, (100, 80, 0))
            rect = title.get_rect(center=(512, 310))
            self.screen.blit(shadow, (rect.x + 2, rect.y + 2))
            self.screen.blit(title, rect)

        # 副标题
        if self.font:
            sub = self.font.render("— 辉耀大陆战记 —", True, (180, 160, 100))
            rect = sub.get_rect(center=(512, 360))
            self.screen.blit(sub, rect)

        # 菜单选项
        if self.font:
            hint = self.font.render("Enter - 新游戏", True, (200, 200, 200))
            rect = hint.get_rect(center=(512, 480))
            self.screen.blit(hint, rect)

            from game.save_system import has_save
            if has_save():
                load_hint = self.font.render("L - 读取存档", True, (200, 200, 200))
                rect = load_hint.get_rect(center=(512, 510))
                self.screen.blit(load_hint, rect)

        # 版本
        if self.small_font:
            ver = self.small_font.render("v0.1 - Development Build", True, (80, 80, 80))
            self.screen.blit(ver, (10, 750))

    def render_battle_ui(self, combat):
        """渲染战斗UI覆盖层"""
        # 顶部信息栏
        top_bar = pygame.Rect(0, 0, 1024, 32)
        pygame.draw.rect(self.screen, (10, 10, 30, 200), top_bar)
        pygame.draw.line(self.screen, (200, 170, 80), (0, 32), (1024, 32), 1)

        if self.font:
            phase_text = "我方回合" if combat.phase == "player" else "敌方行动中..."
            phase_color = (100, 200, 255) if combat.phase == "player" else (255, 100, 100)
            turn_surf = self.font.render(f"第 {combat.turn} 回合", True, (220, 220, 220))
            phase_surf = self.font.render(phase_text, True, phase_color)
            self.screen.blit(turn_surf, (10, 6))
            self.screen.blit(phase_surf, (120, 6))

            # 存活数量
            p_alive = sum(1 for u in combat.units if u.team == "player" and u.alive)
            e_alive = sum(1 for u in combat.units if u.team == "enemy" and u.alive)
            count_text = f"我方: {p_alive}  敌方: {e_alive}"
            count_surf = self.font.render(count_text, True, (200, 200, 200))
            self.screen.blit(count_surf, (900 - count_surf.get_width(), 6))

        # 选中单位详情面板
        if combat.selected_unit and combat.selected_unit.alive:
            self._render_unit_panel(combat.selected_unit)

        # 操作提示
        if self.small_font:
            hints = "WASD:移动视角  左键:选择/确认  右键:取消  Space:结束回合"
            hint_surf = self.small_font.render(hints, True, (120, 120, 120))
            self.screen.blit(hint_surf, (10, 750))

    def _render_unit_panel(self, bu):
        """渲染单位详细信息面板"""
        panel_x = 780
        panel_y = 40
        panel_w = 235
        panel_h = 130

        # 背景
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        s = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        s.fill((15, 15, 35, 220))
        self.screen.blit(s, (panel_x, panel_y))
        border_color = (100, 180, 255) if bu.team == "player" else (255, 100, 100)
        pygame.draw.rect(self.screen, border_color, panel_rect, 1)

        if not self.font or not self.small_font:
            return

        y = panel_y + 8
        # 名字和等级
        name_text = f"{bu.name}  Lv.{bu.level}"
        name_surf = self.font.render(name_text, True, (255, 220, 100))
        self.screen.blit(name_surf, (panel_x + 10, y))
        y += 24

        # 职业
        class_surf = self.small_font.render(f"职业: {bu.unit.unit_class.name}", True, (180, 180, 180))
        self.screen.blit(class_surf, (panel_x + 10, y))
        y += 20

        # HP条
        hp_ratio = bu.hp / bu.max_hp
        hp_text = f"HP: {bu.hp}/{bu.max_hp}"
        hp_surf = self.small_font.render(hp_text, True, (255, 255, 255))
        self.screen.blit(hp_surf, (panel_x + 10, y))
        bar_x = panel_x + 100
        bar_w = 120
        pygame.draw.rect(self.screen, (40, 40, 40), (bar_x, y + 2, bar_w, 12))
        hp_color = (50, 220, 50) if hp_ratio > 0.5 else (220, 220, 50) if hp_ratio > 0.25 else (220, 50, 50)
        pygame.draw.rect(self.screen, hp_color, (bar_x, y + 2, int(bar_w * hp_ratio), 12))
        y += 20

        # 属性
        stats_text = f"攻:{bu.strength} 防:{bu.defense} 速:{bu.speed} 移:{bu.move_range}"
        stats_surf = self.small_font.render(stats_text, True, (180, 200, 180))
        self.screen.blit(stats_surf, (panel_x + 10, y))
        y += 20

        range_text = f"射程:{bu.attack_range}  {'飞行' if bu.is_flying else '地面'}"
        range_surf = self.small_font.render(range_text, True, (180, 180, 200))
        self.screen.blit(range_surf, (panel_x + 10, y))

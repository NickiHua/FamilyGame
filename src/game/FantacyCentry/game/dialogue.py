"""对话/剧情系统"""
import pygame


class DialogueSystem:
    def __init__(self, engine):
        self.engine = engine
        self.active = False
        self.lines = []
        self.current_line = 0
        self.font = None
        self.name_font = None
        self._init_font()
        # 打字机效果
        self.char_index = 0
        self.char_timer = 0
        self.char_speed = 0.03  # 每字符时间
        self.full_text_shown = False

    def _init_font(self):
        try:
            self.font = pygame.font.SysFont("simsun", 22)
            self.name_font = pygame.font.SysFont("simsun", 20, bold=True)
        except Exception:
            self.font = pygame.font.Font(None, 22)
            self.name_font = pygame.font.Font(None, 20)

    def load_lines(self, lines):
        """直接加载对话行"""
        self.lines = lines
        self.current_line = 0
        self.active = True
        self.char_index = 0
        self.char_timer = 0
        self.full_text_shown = False

    def handle_event(self, event):
        if not self.active:
            return
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            if not self.full_text_shown:
                # 快进显示全文
                self.full_text_shown = True
                if self.lines and self.current_line < len(self.lines):
                    self.char_index = len(self.lines[self.current_line].get("text", ""))
            else:
                # 下一句
                self.current_line += 1
                self.char_index = 0
                self.char_timer = 0
                self.full_text_shown = False
                if self.current_line >= len(self.lines):
                    self.active = False
                    self.engine.on_dialogue_complete()

    def update(self, dt):
        if not self.active or self.full_text_shown:
            return
        if self.current_line >= len(self.lines):
            return

        text = self.lines[self.current_line].get("text", "")
        self.char_timer += dt
        while self.char_timer >= self.char_speed and self.char_index < len(text):
            self.char_timer -= self.char_speed
            self.char_index += 1
        if self.char_index >= len(text):
            self.full_text_shown = True

    def render(self, screen):
        if not self.active or not self.lines:
            return
        if self.current_line >= len(self.lines):
            return

        line = self.lines[self.current_line]
        speaker = line.get("speaker", "")
        text = line.get("text", "")

        # 半透明黑背景
        overlay = pygame.Surface((1024, 768), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        screen.blit(overlay, (0, 0))

        # 对话框背景
        box_rect = pygame.Rect(40, 560, 944, 180)
        pygame.draw.rect(screen, (15, 15, 35), box_rect)
        pygame.draw.rect(screen, (200, 170, 80), box_rect, 2)
        # 圆角装饰
        pygame.draw.rect(screen, (200, 170, 80), (40, 556, 944, 4))

        # 名牌
        if speaker and self.name_font:
            name_bg = pygame.Rect(55, 540, len(speaker) * 22 + 20, 30)
            pygame.draw.rect(screen, (40, 30, 15), name_bg)
            pygame.draw.rect(screen, (200, 170, 80), name_bg, 1)
            name_surf = self.name_font.render(speaker, True, (255, 220, 100))
            screen.blit(name_surf, (65, 545))

        # 对话文本（打字机效果）
        if text and self.font:
            display_text = text[:self.char_index]
            # 自动换行
            max_width = 900
            lines_to_draw = self._wrap_text(display_text, max_width)
            for i, line_text in enumerate(lines_to_draw):
                text_surf = self.font.render(line_text, True, (240, 240, 240))
                screen.blit(text_surf, (65, 580 + i * 30))

        # 继续提示
        if self.full_text_shown:
            if self.font:
                hint = self.font.render("▼", True, (200, 200, 100))
                screen.blit(hint, (960, 720))

    def _wrap_text(self, text, max_width):
        """简单的文字换行"""
        if not self.font:
            return [text]
        lines = []
        current = ""
        for char in text:
            test = current + char
            if self.font.size(test)[0] > max_width:
                lines.append(current)
                current = char
            else:
                current = test
        if current:
            lines.append(current)
        return lines if lines else [""]

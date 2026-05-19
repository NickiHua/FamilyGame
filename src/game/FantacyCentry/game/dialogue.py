"""对话/剧情系统"""
import pygame
import json
import os


class DialogueSystem:
    def __init__(self):
        self.active = False
        self.lines = []
        self.current_line = 0
        self.font = None
        self._init_font()

    def _init_font(self):
        try:
            self.font = pygame.font.SysFont("simsun", 20)
        except Exception:
            self.font = pygame.font.Font(None, 20)

    def load_dialogue(self, chapter_id, scene_id):
        """加载对话脚本"""
        path = os.path.join("data", "chapters", f"ch{chapter_id}", f"scene_{scene_id}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.lines = data.get("lines", [])
        else:
            self.lines = []
        self.current_line = 0
        self.active = True

    def load_lines(self, lines):
        """直接加载对话行"""
        self.lines = lines
        self.current_line = 0
        self.active = True

    def handle_event(self, event):
        if not self.active:
            return
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            self.current_line += 1
            if self.current_line >= len(self.lines):
                self.active = False

    def update(self, dt):
        pass

    def render(self, screen):
        if not self.active or not self.lines:
            return
        if self.current_line >= len(self.lines):
            return

        line = self.lines[self.current_line]
        speaker = line.get("speaker", "")
        text = line.get("text", "")

        # 对话框背景
        box_rect = pygame.Rect(50, 550, 924, 150)
        pygame.draw.rect(screen, (20, 20, 40), box_rect)
        pygame.draw.rect(screen, (200, 170, 80), box_rect, 2)

        # 说话者名字
        if speaker and self.font:
            name_surf = self.font.render(speaker, True, (255, 220, 100))
            screen.blit(name_surf, (70, 560))

        # 对话文本
        if text and self.font:
            text_surf = self.font.render(text, True, (255, 255, 255))
            screen.blit(text_surf, (70, 590))

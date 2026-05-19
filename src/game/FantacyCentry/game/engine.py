"""游戏主循环引擎"""
import pygame
import os
import json
from game.map_system import MapSystem
from game.ui import UIManager
from game.combat import CombatManager
from game.world_map import WorldMap
from game.dialogue import DialogueSystem
from game.unit import Unit, CLASSES, create_party
from game.save_system import save_game, load_game, has_save

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
STATE_BATTLE_RESULT = "battle_result"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class GameEngine:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("幻世纪")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = STATE_TITLE

        self.ui = UIManager(self.screen)
        self.combat = CombatManager(self)
        self.world_map = WorldMap(self)
        self.dialogue = DialogueSystem(self)

        # 游戏数据
        self.party = create_party()
        self.available_party = self.party[:2]  # 初始只有陆离和苏瑶
        self.current_chapter = 0
        self.completed_stages = set()

        # 对话结束后的回调
        self._after_dialogue = None
        self._battle_result_timer = 0

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
                    if self.state == STATE_BATTLE:
                        # 退出战斗回大地图（调试用）
                        self.state = STATE_WORLD_MAP
                    else:
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
        elif self.state == STATE_BATTLE_RESULT:
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                self.state = STATE_WORLD_MAP

    def _handle_title_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.state = STATE_WORLD_MAP
            elif event.key == pygame.K_l and has_save():
                load_game(self)
                self.state = STATE_WORLD_MAP

    def start_battle(self, stage_id):
        """从大地图启动战斗"""
        map_path = os.path.join(BASE_DIR, "data", "maps", f"{stage_id}.json")
        if os.path.exists(map_path):
            with open(map_path, "r", encoding="utf-8") as f:
                battle_data = json.load(f)
            # 检查是否有战前对话
            pre_dialogue = battle_data.get("pre_dialogue")
            if pre_dialogue and stage_id not in self.completed_stages:
                self._load_dialogue(battle_data.get("chapter", 0), pre_dialogue)
                self._after_dialogue = lambda: self._start_combat(battle_data)
            else:
                self._start_combat(battle_data)
        else:
            # 生成默认战斗
            self._start_generated_battle(stage_id)

    def _start_combat(self, battle_data):
        """实际开始战斗"""
        self.combat.load_battle(battle_data, self.available_party)
        self.state = STATE_BATTLE

    def _start_generated_battle(self, stage_id):
        """为没有地图文件的关卡生成战斗"""
        from game.battle_generator import generate_battle
        battle_data = generate_battle(stage_id, self.available_party)

        # 尝试加载预设对话
        if stage_id not in self.completed_stages:
            chapter = self._get_chapter_from_stage(stage_id)
            dialogue_path = os.path.join(BASE_DIR, "data", "chapters", f"ch{chapter}", f"{stage_id}_pre.json")
            if os.path.exists(dialogue_path):
                with open(dialogue_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.dialogue.load_lines(data.get("lines", []))
                self.state = STATE_DIALOGUE
                self._after_dialogue = lambda: self._start_combat(battle_data)
                return

        self.combat.load_battle(battle_data, self.available_party)
        self.state = STATE_BATTLE

    def _get_chapter_from_stage(self, stage_id):
        """从stage_id推算章节号"""
        if "prologue" in stage_id or "free_0" in stage_id:
            return 0
        elif "ch1" in stage_id or "free_1" in stage_id:
            return 1
        elif "ch2" in stage_id or "free_2" in stage_id:
            return 2
        elif "ch3" in stage_id or "free_3" in stage_id:
            return 3
        elif "ch4" in stage_id or "free_4" in stage_id:
            return 4
        return 0

    def on_battle_complete(self, victory, stage_id):
        """战斗结束回调"""
        if victory:
            self.completed_stages.add(stage_id)
            self.world_map.complete_node(stage_id)
            # 检查新角色加入
            self._check_new_recruits(stage_id)
            # 更新章节进度
            ch = self._get_chapter_from_stage(stage_id)
            if ch > self.current_chapter:
                self.current_chapter = ch
            # 自动存档
            save_game(self)
        self.state = STATE_BATTLE_RESULT
        self._battle_victory = victory

    def _check_new_recruits(self, stage_id):
        """检查是否有新角色加入"""
        recruit_map = {
            "ch1_2": 5,   # 白鹤 (index 5)
            "ch1_3": 2,   # 凌霜 (index 2)
            "ch1_5": 3,   # 石头 (index 3)
            "ch2_1": 4,   # 赵铁柱 (index 4)
            "ch2_3": 6,   # 月影 (index 6)
            "ch2_5": 7,   # 雷恩 (index 7)
            "ch3_1": 8,   # 柳如烟 (index 8)
            "ch3_4": 9,   # 玄武 (index 9)
        }
        if stage_id in recruit_map:
            idx = recruit_map[stage_id]
            if self.party[idx] not in self.available_party:
                self.available_party.append(self.party[idx])

    def _load_dialogue(self, chapter, scene_id):
        """加载并启动对话"""
        ch_path = os.path.join(BASE_DIR, "data", "chapters", f"ch{chapter}", f"{scene_id}.json")
        if os.path.exists(ch_path):
            with open(ch_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.dialogue.load_lines(data.get("lines", []))
        else:
            # 生成占位对话
            self.dialogue.load_lines([
                {"speaker": "旁白", "text": f"[{scene_id}]"}
            ])
        self.state = STATE_DIALOGUE

    def on_dialogue_complete(self):
        """对话结束回调"""
        if self._after_dialogue:
            cb = self._after_dialogue
            self._after_dialogue = None
            cb()
        else:
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
        elif self.state == STATE_BATTLE_RESULT:
            self._render_battle_result()

        pygame.display.flip()

    def _render_battle_result(self):
        self.screen.fill((10, 10, 30))
        if self._battle_victory:
            text = "战 斗 胜 利 ！"
            color = (255, 215, 0)
        else:
            text = "战 斗 失 败..."
            color = (200, 50, 50)
        if self.ui.title_font:
            surf = self.ui.title_font.render(text, True, color)
            rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40))
            self.screen.blit(surf, rect)
        if self.ui.font:
            hint = self.ui.font.render("按任意键继续", True, (180, 180, 180))
            rect = hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40))
            self.screen.blit(hint, rect)

"""战斗系统 - 完整回合制战棋"""
import pygame
import random
from game.map_system import MapSystem, TILE_SIZE
from game.unit import Unit, CLASSES

# 战斗阶段
PHASE_PLAYER = "player"
PHASE_ENEMY = "enemy"

# 战斗子状态
IDLE = "idle"
UNIT_SELECTED = "unit_selected"
ACTION_MENU = "action_menu"
ATTACK_TARGET = "attack_target"
ENEMY_TURN = "enemy_turn"


class BattleUnit:
    """战斗中的单位包装"""
    def __init__(self, unit, x, y, team="player", ai_type="aggressive"):
        self.unit = unit
        self.x = x
        self.y = y
        self.team = team
        self.acted = False
        self.moved = False
        self.hp = unit.max_hp
        self.max_hp = unit.max_hp
        self.alive = True
        self.ai_type = ai_type

    @property
    def name(self):
        return self.unit.name

    @property
    def move_range(self):
        return self.unit.move_range

    @property
    def attack_range(self):
        return self.unit.attack_range

    @property
    def is_flying(self):
        return self.unit.is_flying

    @property
    def strength(self):
        return self.unit.strength

    @property
    def magic(self):
        return self.unit.magic

    @property
    def defense(self):
        return self.unit.defense

    @property
    def speed(self):
        return self.unit.speed

    @property
    def level(self):
        return self.unit.level

    def take_damage(self, damage):
        self.hp = max(0, self.hp - damage)
        if self.hp <= 0:
            self.alive = False
        return damage

    def heal(self, amount):
        actual = min(amount, self.max_hp - self.hp)
        self.hp += actual
        return actual

    def reset_turn(self):
        self.acted = False
        self.moved = False


class DamagePopup:
    """伤害数字弹出"""
    def __init__(self, x, y, text, color=(255, 255, 255)):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.timer = 1.0
        self.offset_y = 0


class CombatManager:
    def __init__(self, engine):
        self.engine = engine
        self.map_system = MapSystem()
        self.units = []
        self.phase = PHASE_PLAYER
        self.turn = 1
        self.selected_unit = None
        self.move_cells = set()
        self.attack_cells = set()
        self.state = IDLE
        self.stage_id = ""
        self.victory_condition = "defeat_all"

        # 摄像机
        self.camera_x = 0
        self.camera_y = 0

        # 动画/UI
        self.damage_popups = []
        self.action_menu_items = ["攻击", "待机"]
        self.action_menu_index = 0
        self.enemy_action_timer = 0
        self.enemy_queue = []

        # 原始位置（用于取消移动）
        self._orig_x = 0
        self._orig_y = 0

    def load_battle(self, battle_data, party):
        """加载关卡"""
        self.stage_id = battle_data.get("id", "unknown")
        self.victory_condition = battle_data.get("victory", "defeat_all")
        self.map_system.load_map(battle_data)
        self.units = []
        self.turn = 1
        self.phase = PHASE_PLAYER
        self.state = IDLE
        self.damage_popups = []
        self.selected_unit = None
        self.move_cells = set()
        self.attack_cells = set()

        # 加载玩家单位
        for pdata in battle_data.get("player_units", []):
            unit_obj = None
            for p in party:
                if p.name == pdata["name"]:
                    unit_obj = p
                    break
            if unit_obj is None:
                cls = CLASSES.get(pdata.get("class", "swordsman"))
                unit_obj = Unit(pdata["name"], cls, "player", pdata.get("level", 1))
            bu = BattleUnit(unit_obj, pdata["x"], pdata["y"], "player")
            self.units.append(bu)

        # 加载敌方单位
        for edata in battle_data.get("enemy_units", []):
            cls = CLASSES.get(edata.get("class", "swordsman"))
            unit_obj = Unit(edata["name"], cls, "enemy", edata.get("level", 1))
            for _ in range(edata.get("level", 1) - 1):
                unit_obj.level_up()
            unit_obj.level = edata.get("level", 1)
            bu = BattleUnit(unit_obj, edata["x"], edata["y"], "enemy", edata.get("ai", "aggressive"))
            self.units.append(bu)

        # 居中摄像机
        players = [u for u in self.units if u.team == "player"]
        if players:
            avg_x = sum(u.x for u in players) / len(players)
            avg_y = sum(u.y for u in players) / len(players)
            self.camera_x = int(avg_x * TILE_SIZE - 512)
            self.camera_y = int(avg_y * TILE_SIZE - 384)

    def handle_event(self, event):
        if self.phase == PHASE_ENEMY:
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._handle_left_click(event.pos)
            elif event.button == 3:
                self._handle_right_click()
        elif event.type == pygame.KEYDOWN:
            self._handle_key(event.key)

    def _handle_left_click(self, pos):
        mx, my = pos
        gx = (mx + self.camera_x) // TILE_SIZE
        gy = (my + self.camera_y) // TILE_SIZE

        if self.state == IDLE:
            unit = self._get_unit_at(gx, gy)
            if unit and unit.team == "player" and not unit.acted:
                self._select_unit(unit)
            elif unit and unit.team == "enemy":
                self.selected_unit = unit

        elif self.state == UNIT_SELECTED:
            if (gx, gy) in self.move_cells:
                occupied = self._get_unit_at(gx, gy)
                if occupied is None or occupied == self.selected_unit:
                    self._orig_x = self.selected_unit.x
                    self._orig_y = self.selected_unit.y
                    self.selected_unit.x = gx
                    self.selected_unit.y = gy
                    self.state = ACTION_MENU
                    self.action_menu_index = 0
                    self._update_action_menu()
            else:
                self._cancel_selection()

        elif self.state == ATTACK_TARGET:
            target = self._get_unit_at(gx, gy)
            if target and target.team == "enemy" and (gx, gy) in self.attack_cells:
                self._execute_attack(self.selected_unit, target)
                self._end_unit_action()
            else:
                self.state = ACTION_MENU

    def _handle_right_click(self):
        if self.state == UNIT_SELECTED:
            self._cancel_selection()
        elif self.state == ACTION_MENU:
            self.selected_unit.x = self._orig_x
            self.selected_unit.y = self._orig_y
            self._select_unit(self.selected_unit)
        elif self.state == ATTACK_TARGET:
            self.state = ACTION_MENU

    def _handle_key(self, key):
        scroll_speed = TILE_SIZE * 3
        if key == pygame.K_a:
            self.camera_x -= scroll_speed
        elif key == pygame.K_d:
            self.camera_x += scroll_speed
        elif key == pygame.K_w:
            self.camera_y -= scroll_speed
        elif key == pygame.K_s:
            self.camera_y += scroll_speed

        if self.state == ACTION_MENU:
            if key == pygame.K_UP:
                self.action_menu_index = (self.action_menu_index - 1) % len(self.action_menu_items)
            elif key == pygame.K_DOWN:
                self.action_menu_index = (self.action_menu_index + 1) % len(self.action_menu_items)
            elif key == pygame.K_RETURN or key == pygame.K_SPACE:
                self._execute_menu_action()

        if self.state == IDLE and key == pygame.K_SPACE:
            self._end_player_phase()

    def _select_unit(self, unit):
        self.selected_unit = unit
        self.move_cells = self.map_system.get_movement_range(
            unit.x, unit.y, unit.move_range, unit.is_flying
        )
        occupied = {(u.x, u.y) for u in self.units if u.alive and u != unit}
        self.move_cells -= occupied
        self.move_cells.add((unit.x, unit.y))
        self.attack_cells = set()
        self.state = UNIT_SELECTED

    def _update_action_menu(self):
        self.action_menu_items = []
        atk_range = self.map_system.get_attack_range(
            self.selected_unit.x, self.selected_unit.y,
            1, self.selected_unit.attack_range
        )
        enemies_in_range = [u for u in self.units
                           if u.team == "enemy" and u.alive and (u.x, u.y) in atk_range]
        if enemies_in_range:
            self.action_menu_items.append("攻击")

        if "heal" in self.selected_unit.unit.unit_class.traits:
            heal_range = self.map_system.get_attack_range(
                self.selected_unit.x, self.selected_unit.y, 1, 3
            )
            allies_hurt = [u for u in self.units
                          if u.team == "player" and u.alive and u.hp < u.max_hp
                          and (u.x, u.y) in heal_range]
            if allies_hurt:
                self.action_menu_items.append("治疗")

        self.action_menu_items.append("待机")
        self.action_menu_index = 0

    def _execute_menu_action(self):
        action = self.action_menu_items[self.action_menu_index]
        if action == "攻击":
            self.attack_cells = self.map_system.get_attack_range(
                self.selected_unit.x, self.selected_unit.y,
                1, self.selected_unit.attack_range
            )
            self.state = ATTACK_TARGET
        elif action == "治疗":
            heal_range = self.map_system.get_attack_range(
                self.selected_unit.x, self.selected_unit.y, 1, 3
            )
            allies_hurt = [u for u in self.units
                          if u.team == "player" and u.alive and u.hp < u.max_hp
                          and (u.x, u.y) in heal_range]
            if allies_hurt:
                target = min(allies_hurt, key=lambda u: u.hp / u.max_hp)
                amount = self.selected_unit.magic + 10
                healed = target.heal(amount)
                self._add_popup(target.x, target.y, f"+{healed}", (100, 255, 100))
            self._end_unit_action()
        elif action == "待机":
            self._end_unit_action()

    def _execute_attack(self, attacker, defender):
        base_dmg = attacker.strength - defender.defense // 2
        dmg = max(1, base_dmg + random.randint(-2, 3))

        tile = self.map_system.get_tile(defender.x, defender.y)
        if tile:
            dmg = max(1, dmg - tile.defense_bonus)

        if "anti_air" in attacker.unit.unit_class.traits and defender.is_flying:
            dmg = int(dmg * 1.5)

        if "backstab" in attacker.unit.unit_class.traits:
            dmg = int(dmg * 1.8)

        actual_dmg = defender.take_damage(dmg)
        self._add_popup(defender.x, defender.y, str(actual_dmg), (255, 80, 80))

        attacker.unit.gain_exp(30 if not defender.alive else 15)

        # 反击
        if defender.alive and "counter" in defender.unit.unit_class.traits:
            dist = abs(attacker.x - defender.x) + abs(attacker.y - defender.y)
            if dist <= defender.attack_range:
                counter_dmg = max(1, defender.strength - attacker.defense // 2 + random.randint(-2, 2))
                attacker.take_damage(counter_dmg)
                self._add_popup(attacker.x, attacker.y, str(counter_dmg), (255, 150, 50))

    def _add_popup(self, gx, gy, text, color):
        self.damage_popups.append(DamagePopup(gx, gy, text, color))

    def _cancel_selection(self):
        self.selected_unit = None
        self.move_cells = set()
        self.attack_cells = set()
        self.state = IDLE

    def _get_unit_at(self, x, y):
        for unit in self.units:
            if unit.alive and unit.x == x and unit.y == y:
                return unit
        return None

    def _end_unit_action(self):
        if self.selected_unit:
            self.selected_unit.acted = True
        self._cancel_selection()

        if self._check_battle_end():
            return

        player_units = [u for u in self.units if u.team == "player" and u.alive]
        if all(u.acted for u in player_units):
            self._end_player_phase()

    def _end_player_phase(self):
        self.phase = PHASE_ENEMY
        self.state = ENEMY_TURN
        self.enemy_queue = [u for u in self.units if u.team == "enemy" and u.alive]
        self.enemy_action_timer = 0.5

    def _process_enemy_action(self, enemy):
        players = [u for u in self.units if u.team == "player" and u.alive]
        if not players:
            return

        if enemy.ai_type == "defensive":
            for p in players:
                dist = abs(p.x - enemy.x) + abs(p.y - enemy.y)
                if dist <= enemy.attack_range:
                    self._execute_attack(enemy, p)
                    return
        else:
            target = min(players, key=lambda p: abs(p.x - enemy.x) + abs(p.y - enemy.y))
            move_range = self.map_system.get_movement_range(
                enemy.x, enemy.y, enemy.move_range, enemy.is_flying
            )
            occupied = {(u.x, u.y) for u in self.units if u.alive and u != enemy}

            best_pos = (enemy.x, enemy.y)
            best_dist = abs(target.x - enemy.x) + abs(target.y - enemy.y)

            for (mx, my) in move_range:
                if (mx, my) in occupied:
                    continue
                d = abs(target.x - mx) + abs(target.y - my)
                if d < best_dist:
                    best_dist = d
                    best_pos = (mx, my)

            enemy.x, enemy.y = best_pos

            dist = abs(target.x - enemy.x) + abs(target.y - enemy.y)
            if dist <= enemy.attack_range:
                self._execute_attack(enemy, target)

    def _start_player_phase(self):
        self.phase = PHASE_PLAYER
        self.turn += 1
        self.state = IDLE
        for unit in self.units:
            if unit.team == "player":
                unit.reset_turn()

    def _check_battle_end(self):
        enemies_alive = [u for u in self.units if u.team == "enemy" and u.alive]
        players_alive = [u for u in self.units if u.team == "player" and u.alive]

        if not enemies_alive:
            self.engine.on_battle_complete(True, self.stage_id)
            return True
        if not players_alive:
            self.engine.on_battle_complete(False, self.stage_id)
            return True
        return False

    def update(self, dt):
        for popup in self.damage_popups[:]:
            popup.timer -= dt
            popup.offset_y -= 40 * dt
            if popup.timer <= 0:
                self.damage_popups.remove(popup)

        if self.phase == PHASE_ENEMY:
            self.enemy_action_timer -= dt
            if self.enemy_action_timer <= 0:
                if self.enemy_queue:
                    enemy = self.enemy_queue.pop(0)
                    self._process_enemy_action(enemy)
                    self.enemy_action_timer = 0.4
                    if self._check_battle_end():
                        return
                else:
                    self._start_player_phase()

    def render(self, screen):
        self.map_system.render(screen, self.camera_x, self.camera_y)

        # 移动范围
        for (gx, gy) in self.move_cells:
            rect = pygame.Rect(gx * TILE_SIZE - self.camera_x, gy * TILE_SIZE - self.camera_y, TILE_SIZE, TILE_SIZE)
            s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            s.fill((0, 120, 255, 60))
            screen.blit(s, rect)

        # 攻击范围
        for (gx, gy) in self.attack_cells:
            rect = pygame.Rect(gx * TILE_SIZE - self.camera_x, gy * TILE_SIZE - self.camera_y, TILE_SIZE, TILE_SIZE)
            s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            s.fill((255, 50, 50, 60))
            screen.blit(s, rect)

        # 单位
        for unit in self.units:
            if not unit.alive:
                continue
            sx = unit.x * TILE_SIZE - self.camera_x
            sy = unit.y * TILE_SIZE - self.camera_y

            if unit.team == "player":
                color = (60, 140, 255)
                outline = (30, 80, 180)
            else:
                color = (220, 60, 60)
                outline = (150, 30, 30)

            if unit.acted:
                color = tuple(c // 2 for c in color)

            unit_rect = pygame.Rect(sx + 2, sy + 2, TILE_SIZE - 4, TILE_SIZE - 4)
            pygame.draw.rect(screen, color, unit_rect)
            pygame.draw.rect(screen, outline, unit_rect, 2)

            if unit.is_flying:
                pygame.draw.polygon(screen, (255, 255, 200), [
                    (sx + TILE_SIZE // 2, sy + 2),
                    (sx + TILE_SIZE - 4, sy + 10),
                    (sx + 4, sy + 10)
                ])

            # HP条
            hp_ratio = unit.hp / unit.max_hp
            hp_bar_w = TILE_SIZE - 6
            pygame.draw.rect(screen, (40, 40, 40), (sx + 3, sy + TILE_SIZE - 6, hp_bar_w, 4))
            hp_color = (50, 220, 50) if hp_ratio > 0.5 else (220, 220, 50) if hp_ratio > 0.25 else (220, 50, 50)
            pygame.draw.rect(screen, hp_color, (sx + 3, sy + TILE_SIZE - 6, int(hp_bar_w * hp_ratio), 4))

        # 选中高亮
        if self.selected_unit and self.selected_unit.alive:
            sx = self.selected_unit.x * TILE_SIZE - self.camera_x
            sy = self.selected_unit.y * TILE_SIZE - self.camera_y
            pygame.draw.rect(screen, (255, 255, 100), (sx, sy, TILE_SIZE, TILE_SIZE), 2)

        # 伤害弹出
        try:
            popup_font = pygame.font.SysFont("arial", 16, bold=True)
        except Exception:
            popup_font = pygame.font.Font(None, 16)
        for popup in self.damage_popups:
            px = popup.x * TILE_SIZE - self.camera_x + TILE_SIZE // 2
            py = popup.y * TILE_SIZE - self.camera_y + popup.offset_y
            surf = popup_font.render(popup.text, True, popup.color)
            screen.blit(surf, (px - surf.get_width() // 2, int(py)))

        # 行动菜单
        if self.state == ACTION_MENU:
            self._render_action_menu(screen)

    def _render_action_menu(self, screen):
        menu_x = self.selected_unit.x * TILE_SIZE - self.camera_x + TILE_SIZE + 5
        menu_y = self.selected_unit.y * TILE_SIZE - self.camera_y

        try:
            menu_font = pygame.font.SysFont("simsun", 16)
        except Exception:
            menu_font = pygame.font.Font(None, 16)

        menu_w = 80
        menu_h = len(self.action_menu_items) * 28 + 8
        bg_rect = pygame.Rect(menu_x, menu_y, menu_w, menu_h)
        pygame.draw.rect(screen, (20, 20, 40), bg_rect)
        pygame.draw.rect(screen, (200, 170, 80), bg_rect, 2)

        for i, item in enumerate(self.action_menu_items):
            color = (255, 255, 100) if i == self.action_menu_index else (200, 200, 200)
            prefix = "> " if i == self.action_menu_index else "  "
            surf = menu_font.render(prefix + item, True, color)
            screen.blit(surf, (menu_x + 8, menu_y + 6 + i * 28))

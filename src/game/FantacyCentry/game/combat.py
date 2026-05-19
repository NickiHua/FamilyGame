"""战斗系统"""
import pygame
import random
from game.map_system import MapSystem, TILE_SIZE
from game.unit import Unit

# 战斗阶段
PHASE_PLAYER = "player"
PHASE_ENEMY = "enemy"


class CombatManager:
    def __init__(self):
        self.map_system = MapSystem()
        self.units = []
        self.phase = PHASE_PLAYER
        self.turn = 1
        self.selected_unit = None
        self.move_range = set()
        self.attack_range = set()
        self.state = "idle"  # idle, unit_selected, moving, attacking, animating

        # 摄像机
        self.camera_x = 0
        self.camera_y = 0

    def load_battle(self, battle_data):
        """加载关卡数据"""
        self.map_system.load_map(battle_data["map"])
        self.units = battle_data.get("units", [])
        self.phase = PHASE_PLAYER
        self.turn = 1

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            grid_x = (mx + self.camera_x) // TILE_SIZE
            grid_y = (my + self.camera_y) // TILE_SIZE
            self._handle_click(grid_x, grid_y)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._cancel_selection()
        elif event.type == pygame.KEYDOWN:
            self._handle_key(event.key)

    def _handle_click(self, gx, gy):
        if self.state == "idle":
            unit = self._get_unit_at(gx, gy)
            if unit and unit.team == PHASE_PLAYER and not unit.acted:
                self.selected_unit = unit
                self.move_range = self.map_system.get_movement_range(
                    unit.x, unit.y, unit.move_range, unit.is_flying
                )
                self.attack_range = self.map_system.get_attack_range(
                    unit.x, unit.y, 1, unit.attack_range
                )
                self.state = "unit_selected"
        elif self.state == "unit_selected":
            if (gx, gy) in self.move_range:
                self._move_unit(self.selected_unit, gx, gy)
                self.state = "attacking"
            else:
                self._cancel_selection()

        elif self.state == "attacking":
            target = self._get_unit_at(gx, gy)
            if target and target.team == "enemy":
                attack_cells = self.map_system.get_attack_range(
                    self.selected_unit.x, self.selected_unit.y,
                    1, self.selected_unit.attack_range
                )
                if (gx, gy) in attack_cells:
                    self._execute_attack(self.selected_unit, target)
            self._end_unit_action()

    def _handle_key(self, key):
        scroll_speed = TILE_SIZE * 2
        if key == pygame.K_LEFT:
            self.camera_x -= scroll_speed
        elif key == pygame.K_RIGHT:
            self.camera_x += scroll_speed
        elif key == pygame.K_UP:
            self.camera_y -= scroll_speed
        elif key == pygame.K_DOWN:
            self.camera_y += scroll_speed
        elif key == pygame.K_SPACE:
            self._end_player_phase()

    def _cancel_selection(self):
        self.selected_unit = None
        self.move_range = set()
        self.attack_range = set()
        self.state = "idle"

    def _get_unit_at(self, x, y):
        for unit in self.units:
            if unit.alive and unit.x == x and unit.y == y:
                return unit
        return None

    def _move_unit(self, unit, x, y):
        unit.x = x
        unit.y = y
        unit.moved = True

    def _execute_attack(self, attacker, defender):
        damage = max(1, attacker.strength - defender.defense + random.randint(-2, 2))
        defender.take_damage(damage)
        attacker.gain_exp(30 if not defender.alive else 10)

    def _end_unit_action(self):
        if self.selected_unit:
            self.selected_unit.acted = True
        self._cancel_selection()

        # 检查是否所有玩家单位已行动
        player_units = [u for u in self.units if u.team == "player" and u.alive]
        if all(u.acted for u in player_units):
            self._end_player_phase()

    def _end_player_phase(self):
        self.phase = PHASE_ENEMY
        self._enemy_turn()
        self._start_player_phase()

    def _enemy_turn(self):
        """简单AI：向最近的玩家单位移动并攻击"""
        enemies = [u for u in self.units if u.team == "enemy" and u.alive]
        players = [u for u in self.units if u.team == "player" and u.alive]

        for enemy in enemies:
            if not players:
                break
            # 找最近的玩家
            target = min(players, key=lambda p: abs(p.x - enemy.x) + abs(p.y - enemy.y))
            dist = abs(target.x - enemy.x) + abs(target.y - enemy.y)

            # 移动靠近
            if dist > enemy.attack_range:
                dx = 1 if target.x > enemy.x else (-1 if target.x < enemy.x else 0)
                dy = 1 if target.y > enemy.y else (-1 if target.y < enemy.y else 0)
                steps = min(enemy.move_range, dist - enemy.attack_range)
                for _ in range(steps):
                    enemy.x += dx
                    enemy.y += dy

            # 攻击
            dist = abs(target.x - enemy.x) + abs(target.y - enemy.y)
            if dist <= enemy.attack_range:
                damage = max(1, enemy.strength - target.defense + random.randint(-2, 2))
                target.take_damage(damage)

    def _start_player_phase(self):
        self.phase = PHASE_PLAYER
        self.turn += 1
        for unit in self.units:
            if unit.team == "player":
                unit.reset_turn()

    def update(self, dt):
        # 移除死亡单位的渲染（保留在列表中用于剧情）
        pass

    def render(self, screen):
        self.map_system.render(screen, self.camera_x, self.camera_y)

        # 绘制移动范围
        for (gx, gy) in self.move_range:
            rect = pygame.Rect(
                gx * TILE_SIZE - self.camera_x,
                gy * TILE_SIZE - self.camera_y,
                TILE_SIZE, TILE_SIZE
            )
            s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            s.fill((0, 100, 255, 80))
            screen.blit(s, rect)

        # 绘制攻击范围
        for (gx, gy) in self.attack_range:
            rect = pygame.Rect(
                gx * TILE_SIZE - self.camera_x,
                gy * TILE_SIZE - self.camera_y,
                TILE_SIZE, TILE_SIZE
            )
            s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            s.fill((255, 50, 50, 60))
            screen.blit(s, rect)

        # 绘制单位
        for unit in self.units:
            if not unit.alive:
                continue
            color = (0, 150, 255) if unit.team == "player" else (255, 60, 60)
            cx = unit.x * TILE_SIZE - self.camera_x + TILE_SIZE // 2
            cy = unit.y * TILE_SIZE - self.camera_y + TILE_SIZE // 2
            pygame.draw.circle(screen, color, (cx, cy), TILE_SIZE // 3)

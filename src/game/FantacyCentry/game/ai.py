"""敌方AI系统"""
import heapq


def astar(map_system, start, goal, flying=False):
    """A*寻路算法"""
    sx, sy = start
    gx, gy = goal

    open_set = [(0, sx, sy)]
    came_from = {}
    g_score = {(sx, sy): 0}

    while open_set:
        _, cx, cy = heapq.heappop(open_set)

        if (cx, cy) == (gx, gy):
            path = []
            while (cx, cy) in came_from:
                path.append((cx, cy))
                cx, cy = came_from[(cx, cy)]
            path.reverse()
            return path

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = cx + dx, cy + dy
            tile = map_system.get_tile(nx, ny)
            if tile is None:
                continue
            if not flying and not tile.passable:
                continue
            cost = 1 if flying else tile.move_cost
            new_g = g_score[(cx, cy)] + cost

            if (nx, ny) not in g_score or new_g < g_score[(nx, ny)]:
                g_score[(nx, ny)] = new_g
                h = abs(nx - gx) + abs(ny - gy)
                heapq.heappush(open_set, (new_g + h, nx, ny))
                came_from[(nx, ny)] = (cx, cy)

    return []  # 无路径


class AIBehavior:
    """AI行为基类"""
    def decide(self, unit, allies, enemies, map_system):
        raise NotImplementedError


class AggressiveAI(AIBehavior):
    """进攻型AI：优先攻击最弱的敌人"""
    def decide(self, unit, allies, enemies, map_system):
        if not enemies:
            return None, None

        # 选目标: HP最低的
        target = min(enemies, key=lambda e: e.hp)
        path = astar(map_system, (unit.x, unit.y), (target.x, target.y), unit.is_flying)

        # 移动到攻击范围内
        move_to = None
        if path:
            steps = min(len(path), unit.move_range)
            if steps > 0:
                move_to = path[steps - 1]

        return move_to, target


class DefensiveAI(AIBehavior):
    """防守型AI：不主动移动，进入范围后攻击"""
    def decide(self, unit, allies, enemies, map_system):
        for enemy in enemies:
            dist = abs(enemy.x - unit.x) + abs(enemy.y - unit.y)
            if dist <= unit.attack_range:
                return None, enemy
        return None, None


class PatrolAI(AIBehavior):
    """巡逻型AI：沿路径移动，发现敌人切换为进攻"""
    def __init__(self, patrol_points):
        self.patrol_points = patrol_points
        self.current_index = 0

    def decide(self, unit, allies, enemies, map_system):
        # 检查是否有敌人在感知范围内
        for enemy in enemies:
            dist = abs(enemy.x - unit.x) + abs(enemy.y - unit.y)
            if dist <= 5:
                return AggressiveAI().decide(unit, allies, enemies, map_system)

        # 巡逻
        if self.patrol_points:
            target_pos = self.patrol_points[self.current_index]
            if (unit.x, unit.y) == target_pos:
                self.current_index = (self.current_index + 1) % len(self.patrol_points)
                target_pos = self.patrol_points[self.current_index]

            path = astar(map_system, (unit.x, unit.y), target_pos, unit.is_flying)
            if path:
                steps = min(len(path), unit.move_range)
                return path[steps - 1], None

        return None, None

"""自动关卡生成器 - 为没有手工地图的关卡生成战斗数据"""
import random

TERRAIN_TYPES = ["plain", "forest", "mountain", "water", "wall"]


def generate_battle(stage_id, party):
    """根据stage_id生成战斗数据"""
    # 解析关卡难度
    difficulty = _get_difficulty(stage_id)
    is_free = "free" in stage_id

    # 地图尺寸
    width = random.randint(12, 18)
    height = random.randint(10, 14)

    # 生成地形
    terrain = _generate_terrain(width, height, difficulty)

    # 玩家单位
    player_units = []
    for i, unit in enumerate(party[:min(len(party), 4 + difficulty)]):
        px = random.randint(1, 3)
        py = random.randint(1 + i, min(height - 2, 2 + i * 2))
        player_units.append({
            "name": unit.name,
            "class": unit.unit_class.name,
            "x": px,
            "y": py,
            "level": unit.level
        })

    # 敌方单位
    enemy_count = 3 + difficulty + (1 if is_free else 0)
    enemy_units = _generate_enemies(width, height, enemy_count, difficulty)

    return {
        "id": stage_id,
        "name": stage_id,
        "width": width,
        "height": height,
        "terrain": terrain,
        "player_units": player_units,
        "enemy_units": enemy_units,
        "victory": "defeat_all",
    }


def _get_difficulty(stage_id):
    """从stage_id推算难度等级"""
    if "prologue" in stage_id or "free_0" in stage_id:
        return 1
    elif "ch1" in stage_id or "free_1" in stage_id:
        return 2
    elif "ch2" in stage_id or "free_2" in stage_id:
        return 3
    elif "ch3" in stage_id or "free_3" in stage_id:
        return 4
    elif "ch4" in stage_id or "free_4" in stage_id:
        return 5
    return 2


def _generate_terrain(width, height, difficulty):
    """程序化生成地形"""
    terrain = [["plain"] * width for _ in range(height)]

    # 随机森林
    forest_count = int(width * height * 0.15)
    for _ in range(forest_count):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        terrain[y][x] = "forest"
        # 小簇
        for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
            if random.random() < 0.4:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    terrain[ny][nx] = "forest"

    # 随机山地
    mountain_count = int(width * height * 0.05)
    for _ in range(mountain_count):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        terrain[y][x] = "mountain"

    # 随机水域（难度高了更多障碍）
    if difficulty >= 3:
        water_count = random.randint(2, 5)
        sx = random.randint(3, width - 4)
        sy = random.randint(3, height - 4)
        for _ in range(water_count):
            if 0 <= sx < width and 0 <= sy < height:
                terrain[sy][sx] = "water"
            sx += random.choice([-1, 0, 1])
            sy += random.choice([-1, 0, 1])

    # 确保玩家出生区是plain
    for y in range(min(3, height)):
        for x in range(min(4, width)):
            terrain[y][x] = "plain"

    return terrain


def _generate_enemies(width, height, count, difficulty):
    """生成敌方单位"""
    enemy_classes = ["swordsman", "archer", "mage", "knight"]
    if difficulty >= 3:
        enemy_classes.extend(["assassin", "gunner"])
    if difficulty >= 4:
        enemy_classes.append("warlock")

    enemies = []
    positions_used = set()

    base_level = max(1, difficulty)

    for i in range(count):
        # 放在地图右半部分
        while True:
            ex = random.randint(width - 5, width - 1)
            ey = random.randint(0, height - 1)
            if (ex, ey) not in positions_used:
                positions_used.add((ex, ey))
                break

        cls = random.choice(enemy_classes)
        level = base_level + random.randint(0, 1)

        # 最后一个是队长（强化）
        name = "帝国兵" if i < count - 1 else "敌方队长"
        ai = "aggressive" if random.random() > 0.3 else "defensive"

        if i == count - 1:
            cls = "knight"
            level += 1
            ai = "aggressive"

        enemies.append({
            "name": name,
            "class": cls,
            "x": ex,
            "y": ey,
            "level": level,
            "ai": ai,
        })

    return enemies

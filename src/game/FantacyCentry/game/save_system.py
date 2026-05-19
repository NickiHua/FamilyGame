"""存档系统"""
import json
import os

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saves")


def save_game(engine, slot=1):
    """保存游戏进度"""
    os.makedirs(SAVE_DIR, exist_ok=True)

    data = {
        "chapter": engine.current_chapter,
        "completed_stages": list(engine.completed_stages),
        "party": [],
    }

    for unit in engine.available_party:
        data["party"].append({
            "name": unit.name,
            "level": unit.level,
            "exp": unit.exp,
            "max_hp": unit.max_hp,
            "strength": unit.strength,
            "magic": unit.magic,
            "defense": unit.defense,
            "resistance": unit.resistance,
            "speed": unit.speed,
        })

    path = os.path.join(SAVE_DIR, f"save_{slot}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True


def load_game(engine, slot=1):
    """读取存档"""
    path = os.path.join(SAVE_DIR, f"save_{slot}.json")
    if not os.path.exists(path):
        return False

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    engine.current_chapter = data.get("chapter", 0)
    engine.completed_stages = set(data.get("completed_stages", []))

    # 恢复角色状态
    for save_unit in data.get("party", []):
        for unit in engine.party:
            if unit.name == save_unit["name"]:
                unit.level = save_unit["level"]
                unit.exp = save_unit["exp"]
                unit.max_hp = save_unit["max_hp"]
                unit.hp = unit.max_hp
                unit.strength = save_unit["strength"]
                unit.magic = save_unit["magic"]
                unit.defense = save_unit["defense"]
                unit.resistance = save_unit["resistance"]
                unit.speed = save_unit["speed"]
                if unit not in engine.available_party:
                    engine.available_party.append(unit)
                break

    # 恢复大地图解锁状态
    for stage_id in engine.completed_stages:
        engine.world_map.complete_node(stage_id)

    return True


def has_save(slot=1):
    """检查是否有存档"""
    path = os.path.join(SAVE_DIR, f"save_{slot}.json")
    return os.path.exists(path)

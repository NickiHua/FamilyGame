"""角色单位系统"""


class UnitClass:
    """职业定义"""
    def __init__(self, name, move, attack_range=1, flying=False, traits=None):
        self.name = name
        self.move = move
        self.attack_range = attack_range
        self.flying = flying
        self.traits = traits or []


# 预定义职业
CLASSES = {
    "swordsman": UnitClass("剑士", move=5, attack_range=1, traits=["counter"]),
    "griffin_rider": UnitClass("狮鹫骑士", move=7, attack_range=1, flying=True, traits=["flying"]),
    "golem": UnitClass("魔物", move=4, attack_range=1, traits=["heavy_armor"]),
    "knight": UnitClass("重甲骑士", move=4, attack_range=1, traits=["guard"]),
    "mage": UnitClass("法师", move=3, attack_range=3, traits=["aoe"]),
    "priest": UnitClass("僧侣", move=4, attack_range=3, traits=["heal"]),
    "assassin": UnitClass("刺客", move=6, attack_range=1, traits=["backstab", "stealth"]),
    "gunner": UnitClass("魔铳士", move=4, attack_range=5, traits=["ammo_switch"]),
    "archer": UnitClass("弓箭手", move=5, attack_range=4, traits=["anti_air", "charge_shot"]),
    "warlock": UnitClass("咒术师", move=3, attack_range=3, traits=["debuff"]),
}


class Unit:
    """战斗单位"""
    def __init__(self, name, unit_class, team="player", level=1):
        self.name = name
        self.unit_class = unit_class
        self.team = team  # "player" or "enemy"
        self.level = level
        self.exp = 0

        # 基础属性
        self.max_hp = 100
        self.hp = 100
        self.max_mp = 30
        self.mp = 30
        self.strength = 10
        self.magic = 10
        self.defense = 8
        self.resistance = 6
        self.speed = 8

        # 状态
        self.x = 0
        self.y = 0
        self.acted = False
        self.moved = False
        self.alive = True

        # 技能列表
        self.skills = []

    @property
    def move_range(self):
        return self.unit_class.move

    @property
    def attack_range(self):
        return self.unit_class.attack_range

    @property
    def is_flying(self):
        return self.unit_class.flying

    def take_damage(self, damage):
        self.hp = max(0, self.hp - damage)
        if self.hp <= 0:
            self.alive = False

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def gain_exp(self, amount):
        self.exp += amount
        while self.exp >= 100:
            self.exp -= 100
            self.level_up()

    def level_up(self):
        self.level += 1
        self.max_hp += 5
        self.hp = self.max_hp
        self.strength += 2
        self.magic += 2
        self.defense += 1
        self.resistance += 1
        self.speed += 1

    def reset_turn(self):
        self.acted = False
        self.moved = False


# 预定义主角团
def create_party():
    """创建主角团"""
    party = [
        _make_unit("陆离", "swordsman", 1),
        _make_unit("苏瑶", "mage", 1),
        _make_unit("凌霜", "griffin_rider", 3),
        _make_unit("岩魔·石头", "golem", 3),
        _make_unit("赵铁柱", "knight", 5),
        _make_unit("白鹤", "priest", 2),
        _make_unit("月影", "assassin", 5),
        _make_unit("雷恩", "gunner", 6),
        _make_unit("柳如烟", "archer", 7),
        _make_unit("玄武", "warlock", 8),
    ]
    return party


def _make_unit(name, class_key, join_level):
    cls = CLASSES[class_key]
    unit = Unit(name, cls, team="player", level=join_level)
    # 按等级调整属性
    for _ in range(join_level - 1):
        unit.level_up()
    unit.level = join_level
    return unit

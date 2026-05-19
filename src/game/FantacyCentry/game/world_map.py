"""大地图系统"""
import pygame


class WorldMapNode:
    def __init__(self, node_id, name, node_type, x, y, chapter=0):
        self.node_id = node_id
        self.name = name
        self.node_type = node_type  # "story", "free_battle", "town"
        self.x = x
        self.y = y
        self.chapter = chapter
        self.unlocked = False
        self.completed = False
        self.connections = []  # list of node_ids


class WorldMap:
    def __init__(self):
        self.nodes = {}
        self.current_node = None
        self.cursor_index = 0
        self.font = None
        self._init_font()
        self._init_default_map()

    def _init_font(self):
        try:
            self.font = pygame.font.SysFont("simsun", 16)
        except Exception:
            self.font = pygame.font.Font(None, 16)

    def _init_default_map(self):
        """初始化序章大地图节点"""
        nodes_data = [
            ("prologue_1", "猎村突袭", "story", 200, 400, 0),
            ("prologue_2", "烈火逃亡", "story", 320, 350, 0),
            ("prologue_3", "荒野伏击", "story", 450, 320, 0),
            ("prologue_free", "荒野练兵场", "free_battle", 380, 420, 0),
            ("ch1_1", "义军营地", "story", 550, 280, 1),
            ("ch1_2", "云隐古道", "story", 650, 240, 1),
            ("ch1_3", "风谷关隘", "story", 750, 200, 1),
        ]
        for nid, name, ntype, x, y, ch in nodes_data:
            self.nodes[nid] = WorldMapNode(nid, name, ntype, x, y, ch)

        # 设置连接
        self.nodes["prologue_1"].connections = ["prologue_2"]
        self.nodes["prologue_2"].connections = ["prologue_3", "prologue_free"]
        self.nodes["prologue_3"].connections = ["ch1_1"]
        self.nodes["prologue_free"].connections = ["prologue_2"]
        self.nodes["ch1_1"].connections = ["ch1_2"]
        self.nodes["ch1_2"].connections = ["ch1_3"]

        # 解锁第一个
        self.nodes["prologue_1"].unlocked = True
        self.current_node = "prologue_1"

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            unlocked_nodes = [n for n in self.nodes.values() if n.unlocked]
            if event.key == pygame.K_LEFT or event.key == pygame.K_UP:
                self.cursor_index = (self.cursor_index - 1) % len(unlocked_nodes)
            elif event.key == pygame.K_RIGHT or event.key == pygame.K_DOWN:
                self.cursor_index = (self.cursor_index + 1) % len(unlocked_nodes)
            elif event.key == pygame.K_RETURN:
                # 选择进入节点
                if unlocked_nodes:
                    self.current_node = unlocked_nodes[self.cursor_index].node_id

    def update(self, dt):
        pass

    def render(self, screen):
        screen.fill((30, 40, 30))

        # 画连接线
        for node in self.nodes.values():
            for conn_id in node.connections:
                if conn_id in self.nodes:
                    conn = self.nodes[conn_id]
                    color = (100, 100, 80) if node.unlocked else (50, 50, 50)
                    pygame.draw.line(screen, color, (node.x, node.y), (conn.x, conn.y), 2)

        # 画节点
        unlocked_list = [n for n in self.nodes.values() if n.unlocked]
        for node in self.nodes.values():
            if node.unlocked:
                if node.node_type == "story":
                    color = (255, 200, 50)
                elif node.node_type == "free_battle":
                    color = (100, 200, 100)
                else:
                    color = (100, 150, 255)
            else:
                color = (60, 60, 60)

            pygame.draw.circle(screen, color, (node.x, node.y), 12)

            if node.completed:
                pygame.draw.circle(screen, (255, 255, 255), (node.x, node.y), 5)

            # 名称
            if self.font and node.unlocked:
                name_surf = self.font.render(node.name, True, (220, 220, 220))
                screen.blit(name_surf, (node.x - 30, node.y + 16))

        # 光标
        if unlocked_list and self.cursor_index < len(unlocked_list):
            sel = unlocked_list[self.cursor_index]
            pygame.draw.circle(screen, (255, 255, 255), (sel.x, sel.y), 16, 2)

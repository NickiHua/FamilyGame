"""大地图系统 - 关卡选择与探索"""
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
    def __init__(self, engine):
        self.engine = engine
        self.nodes = {}
        self.node_list = []  # 有序列表用于导航
        self.cursor_index = 0
        self.font = None
        self.small_font = None
        self._init_font()
        self._init_all_nodes()

    def _init_font(self):
        try:
            self.font = pygame.font.SysFont("simsun", 18)
            self.small_font = pygame.font.SysFont("simsun", 14)
        except Exception:
            self.font = pygame.font.Font(None, 18)
            self.small_font = pygame.font.Font(None, 14)

    def _init_all_nodes(self):
        """初始化全部大地图节点"""
        nodes_data = [
            # 序章
            ("prologue_1", "猎村突袭", "story", 120, 450, 0),
            ("prologue_2", "烈火逃亡", "story", 200, 400, 0),
            ("prologue_3", "荒野伏击", "story", 290, 370, 0),
            ("free_0_1", "荒野练兵场", "free_battle", 220, 470, 0),
            # 第一章
            ("ch1_1", "义军营地", "story", 370, 340, 1),
            ("ch1_2", "云隐古道", "story", 440, 300, 1),
            ("ch1_3", "风谷关隘", "story", 520, 270, 1),
            ("ch1_4", "黑石矿坑", "story", 590, 240, 1),
            ("ch1_5", "魔物觉醒", "story", 660, 260, 1),
            ("ch1_6", "铁蹄平原", "story", 730, 230, 1),
            ("ch1_7", "苍原决战", "story", 810, 200, 1),
            ("free_1_1", "云隐古道(练)", "free_battle", 460, 350, 1),
            ("free_1_2", "风谷猎场", "free_battle", 550, 320, 1),
            # 第二章
            ("ch2_1", "叛将之路", "story", 870, 250, 2),
            ("ch2_2", "地下水道", "story", 900, 310, 2),
            ("ch2_3", "月下追击", "story", 870, 370, 2),
            ("ch2_4", "贫民窟暴动", "story", 830, 420, 2),
            ("ch2_5", "铸造厂", "story", 780, 460, 2),
            ("ch2_6", "教团密室", "story", 730, 490, 2),
            ("ch2_7", "皇宫突围", "story", 680, 510, 2),
            ("ch2_8", "王城城墙", "story", 630, 540, 2),
            ("free_2_1", "地下水道(练)", "free_battle", 920, 370, 2),
            ("free_2_2", "城外据点", "free_battle", 760, 520, 2),
            # 第三章
            ("ch3_1", "南境密林", "story", 200, 550, 3),
            ("ch3_2", "猎族试炼", "story", 270, 580, 3),
            ("ch3_3", "海港保卫战", "story", 350, 600, 3),
            ("ch3_4", "命运之塔", "story", 430, 580, 3),
            ("ch3_5", "封印神殿·东", "story", 510, 560, 3),
            ("ch3_6", "联军集结", "story", 580, 540, 3),
            ("ch3_7", "封印神殿·西", "story", 440, 520, 3),
            ("ch3_8", "叛徒", "story", 360, 500, 3),
            ("ch3_9", "血战长桥", "story", 300, 480, 3),
            ("free_3_1", "南境密林(练)", "free_battle", 220, 610, 3),
            ("free_3_2", "废弃矿洞", "free_battle", 380, 640, 3),
            ("free_3_3", "海港郊外", "free_battle", 470, 630, 3),
            # 终章
            ("ch4_1", "虚无裂隙·入口", "story", 500, 150, 4),
            ("ch4_2", "扭曲战场", "story", 560, 120, 4),
            ("ch4_3", "记忆幻境", "story", 630, 100, 4),
            ("ch4_4", "同伴之心", "story", 700, 80, 4),
            ("ch4_5", "教团本阵", "story", 770, 100, 4),
            ("ch4_6", "邪神祭坛", "story", 830, 120, 4),
            ("ch4_7", "虚无之主降临", "story", 880, 150, 4),
            ("ch4_8", "封印·终焉", "story", 920, 180, 4),
            ("free_4_1", "裂隙边缘", "free_battle", 540, 170, 4),
            ("free_4_2", "虚空回廊", "free_battle", 750, 150, 4),
        ]

        for nid, name, ntype, x, y, ch in nodes_data:
            self.nodes[nid] = WorldMapNode(nid, name, ntype, x, y, ch)

        # 设置连接（按顺序）
        story_chains = [
            ["prologue_1", "prologue_2", "prologue_3"],
            ["prologue_3", "ch1_1", "ch1_2", "ch1_3", "ch1_4", "ch1_5", "ch1_6", "ch1_7"],
            ["ch1_7", "ch2_1", "ch2_2", "ch2_3", "ch2_4", "ch2_5", "ch2_6", "ch2_7", "ch2_8"],
            ["ch2_8", "ch3_1", "ch3_2", "ch3_3", "ch3_4", "ch3_5", "ch3_6"],
            ["ch3_4", "ch3_7", "ch3_8", "ch3_9"],
            ["ch3_6", "ch4_1", "ch4_2", "ch4_3", "ch4_4", "ch4_5", "ch4_6", "ch4_7", "ch4_8"],
        ]
        for chain in story_chains:
            for i in range(len(chain) - 1):
                if chain[i] in self.nodes and chain[i + 1] in self.nodes:
                    self.nodes[chain[i]].connections.append(chain[i + 1])
                    self.nodes[chain[i + 1]].connections.append(chain[i])

        # 自由战斗连接
        free_conns = [
            ("free_0_1", "prologue_2"),
            ("free_1_1", "ch1_2"), ("free_1_2", "ch1_3"),
            ("free_2_1", "ch2_2"), ("free_2_2", "ch2_7"),
            ("free_3_1", "ch3_1"), ("free_3_2", "ch3_3"), ("free_3_3", "ch3_3"),
            ("free_4_1", "ch4_1"), ("free_4_2", "ch4_5"),
        ]
        for fid, sid in free_conns:
            if fid in self.nodes and sid in self.nodes:
                self.nodes[fid].connections.append(sid)
                self.nodes[sid].connections.append(fid)

        # 解锁第一个
        self.nodes["prologue_1"].unlocked = True
        self._update_node_list()

    def _update_node_list(self):
        """更新可用节点列表"""
        self.node_list = [n for n in self.nodes.values() if n.unlocked]
        if self.cursor_index >= len(self.node_list):
            self.cursor_index = max(0, len(self.node_list) - 1)

    def complete_node(self, node_id):
        """完成节点并解锁后续"""
        if node_id in self.nodes:
            self.nodes[node_id].completed = True
            # 解锁相连节点
            for conn_id in self.nodes[node_id].connections:
                if conn_id in self.nodes:
                    self.nodes[conn_id].unlocked = True
            self._update_node_list()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if not self.node_list:
                return
            if event.key == pygame.K_LEFT or event.key == pygame.K_UP:
                self.cursor_index = (self.cursor_index - 1) % len(self.node_list)
            elif event.key == pygame.K_RIGHT or event.key == pygame.K_DOWN:
                self.cursor_index = (self.cursor_index + 1) % len(self.node_list)
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                self._enter_node()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)

    def _handle_click(self, pos):
        mx, my = pos
        for i, node in enumerate(self.node_list):
            if abs(mx - node.x) < 18 and abs(my - node.y) < 18:
                self.cursor_index = i
                self._enter_node()
                return

    def _enter_node(self):
        if not self.node_list:
            return
        node = self.node_list[self.cursor_index]
        # 进入战斗
        self.engine.start_battle(node.node_id)

    def update(self, dt):
        pass

    def render(self, screen):
        # 背景
        screen.fill((25, 35, 25))

        # 标题
        if self.font:
            chapter_names = ["序章", "第一章", "第二章", "第三章", "终章"]
            ch = min(self.engine.current_chapter, 4)
            title = self.font.render(f"大地图 - {chapter_names[ch]}", True, (200, 200, 200))
            screen.blit(title, (10, 10))

        # 连接线
        drawn_lines = set()
        for node in self.nodes.values():
            for conn_id in node.connections:
                if conn_id in self.nodes:
                    line_key = tuple(sorted([node.node_id, conn_id]))
                    if line_key in drawn_lines:
                        continue
                    drawn_lines.add(line_key)
                    conn = self.nodes[conn_id]
                    if node.unlocked and conn.unlocked:
                        color = (100, 120, 80)
                    elif node.unlocked or conn.unlocked:
                        color = (60, 70, 50)
                    else:
                        color = (35, 40, 35)
                    pygame.draw.line(screen, color, (node.x, node.y), (conn.x, conn.y), 2)

        # 节点
        for node in self.nodes.values():
            if not node.unlocked:
                pygame.draw.circle(screen, (40, 40, 40), (node.x, node.y), 8)
                continue

            if node.node_type == "story":
                color = (255, 200, 50) if not node.completed else (120, 100, 40)
            elif node.node_type == "free_battle":
                color = (80, 200, 80)
            else:
                color = (100, 150, 255)

            pygame.draw.circle(screen, color, (node.x, node.y), 12)

            if node.completed:
                pygame.draw.line(screen, (255, 255, 255),
                               (node.x - 4, node.y), (node.x - 1, node.y + 4), 2)
                pygame.draw.line(screen, (255, 255, 255),
                               (node.x - 1, node.y + 4), (node.x + 5, node.y - 3), 2)

            # 名称
            if self.small_font:
                name_surf = self.small_font.render(node.name, True, (200, 200, 200))
                screen.blit(name_surf, (node.x - name_surf.get_width() // 2, node.y + 15))

        # 光标
        if self.node_list and self.cursor_index < len(self.node_list):
            sel = self.node_list[self.cursor_index]
            # 闪烁光标
            pygame.draw.circle(screen, (255, 255, 255), (sel.x, sel.y), 16, 2)
            pygame.draw.circle(screen, (255, 255, 100), (sel.x, sel.y), 18, 1)

        # 底部信息栏
        if self.node_list and self.cursor_index < len(self.node_list):
            sel = self.node_list[self.cursor_index]
            info_rect = pygame.Rect(0, 700, 1024, 68)
            pygame.draw.rect(screen, (20, 20, 40), info_rect)
            pygame.draw.rect(screen, (200, 170, 80), info_rect, 1)
            if self.font:
                type_name = {"story": "主线", "free_battle": "自由战斗", "town": "城镇"}
                info_text = f"{sel.name}  [{type_name.get(sel.node_type, '')}]"
                if sel.completed:
                    info_text += "  (已完成)"
                surf = self.font.render(info_text, True, (255, 255, 255))
                screen.blit(surf, (20, 720))

                hint = self.small_font.render("← → 选择节点  Enter 进入  ", True, (150, 150, 150))
                screen.blit(hint, (20, 745))

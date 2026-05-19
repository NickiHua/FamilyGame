# 幻世纪 (FantacyCentry)

回合制战棋RPG，灵感来源于《幻世录》。

## 环境配置

本项目使用 conda 环境，请确保已安装 [Miniconda](https://docs.conda.io/en/latest/miniconda.html) 或 Anaconda。

```bash
# 激活 game 环境
conda activate game

# 如果尚未创建 game 环境
conda create -n game python=3.11
conda activate game
pip install -r requirements.txt
```

## 运行游戏

```bash
conda activate game
python main.py
```

## 项目结构

```
FantacyCentry/
├── main.py              # 游戏入口
├── requirements.txt     # Python 依赖
├── game/
│   ├── __init__.py
│   ├── engine.py        # 游戏主循环
│   ├── map_system.py    # 地图/网格系统
│   ├── unit.py          # 角色单位
│   ├── combat.py        # 战斗系统
│   ├── ai.py            # 敌方AI
│   ├── dialogue.py      # 对话系统
│   ├── ui.py            # UI渲染
│   ├── camera.py        # 镜头控制
│   └── world_map.py     # 大地图系统
├── data/
│   ├── chapters/        # 剧情脚本(JSON)
│   ├── maps/            # 关卡地图数据
│   └── classes.json     # 职业/角色定义
├── assets/
│   ├── sprites/         # 角色精灵图
│   ├── tiles/           # 地图tile素材
│   ├── portraits/       # 对话头像
│   ├── ui/              # UI素材
│   └── sfx/             # 音效
└── 游戏大纲.md           # 游戏设计文档
```

## 打包为 Windows 可执行文件

```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

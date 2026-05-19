"""幻世纪 - 战棋RPG游戏入口"""
import pygame
import sys
from game.engine import GameEngine


def main():
    pygame.init()
    engine = GameEngine()
    engine.run()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

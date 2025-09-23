import os

from ladder import run_ladder_game

from sc2.player import Bot
from stockfish.stockfish import Stockfish

bot = Stockfish()
race = bot.my_race
protoss_bot = Bot(race, bot)


def main():
    # Ladder game started by LadderManager
    print("Starting ladder game...")
    result, opponentid = run_ladder_game(protoss_bot)
    print(result, " against opponent ", opponentid)


if __name__ == "__main__":
    main()

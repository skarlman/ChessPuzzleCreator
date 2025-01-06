import chess
import chess.pgn
import chess.engine
import io
from pathlib import Path

from ChessPuzzleGenerator import ChessPuzzleGenerator
from chess_api import ChessComAPI
from generate_puzzle_index import generate_puzzle_index


def process_pgn_files():
    puzzle_gen = ChessPuzzleGenerator()
    try:
        pgn_dir = Path("lichessdata")
        if not pgn_dir.exists():
            print("lichessdata directory not found.")
            return

        total_puzzles = 0
        for pgn_file in pgn_dir.glob("*.pgn"):
            print(f"Processing {pgn_file.name}...")
            
            with open(pgn_file) as pgn:
                while True:
                    game = chess.pgn.read_game(pgn)
                    if game is None:  # End of file
                        break
                    
                    if total_puzzles > 100:
                        return total_puzzles

                    # Combine UTC date and time for timestamp
                    date = game.headers.get("UTCDate", "").replace(".", "-")
                    time = game.headers.get("UTCTime", "")
                    timestamp = f"{date} {time}" if date and time else ""

                    # Updated game_info structure to match chess.com format and include Lichess specifics
                    game_info = {
                        "id": game.headers.get("Site", "").split("/")[-1],  # Extract ID from Lichess URL
                        "white": {"username": game.headers.get("White", "Unknown")},
                        "black": {"username": game.headers.get("Black", "Unknown")},
                        "end_time": timestamp,
                        "url": game.headers.get("Site", ""),
                        "white_elo": game.headers.get("WhiteElo", ""),
                        "black_elo": game.headers.get("BlackElo", ""),
                        "opening": game.headers.get("Opening", ""),
                        "eco": game.headers.get("ECO", ""),
                        "pgn": str(game)  # Make sure PGN is included
                    }

                    puzzles = puzzle_gen.find_missed_tactics(game, None)
                    
                    for puzzle in puzzles:
                        puzzle_id = puzzle_gen.save_puzzle(puzzle, game_info)
                        total_puzzles += 1
                        print(f"Created puzzle {puzzle_id}")
        
        return total_puzzles
    finally:
        puzzle_gen.close()

def main():
    total_puzzles = 0

    source = "1" # input("Enter source (1 for chess.com, 2 for lichess PGN files): ")
    
    if source == "1":

        for username in ["Mennborg", "Meea", "skarlman"]:

            puzzle_gen = ChessPuzzleGenerator()
            try:
#                username = input("Enter chess.com username (or press Enter for all players): ").strip() or None
                print(f"Fetching recent games for {username}...")

                games = ChessComAPI.get_player_games(username)

                if not games:
                    print("No games found.")
                    return

                for game_info in games:
                    #if total_puzzles > 30:
                    #    break

                    pgn = ChessComAPI.get_game(game_info)

                    if not pgn:
                        print("Error: No PGN found for this game.")
                        continue

                    game = chess.pgn.read_game(io.StringIO(pgn))
                    puzzles = puzzle_gen.find_missed_tactics(game, username)

                    for puzzle in puzzles:
                        puzzle_id = puzzle_gen.save_puzzle(puzzle, game_info)
                        total_puzzles += 1
                        print(f"Created puzzle {puzzle_id}")

            finally:
                puzzle_gen.close()
    
    elif source == "2":
        total_puzzles = process_pgn_files()
    else:
        print("Invalid source selected")


    print(f"\nTotal puzzles created: {total_puzzles}")

    # Generate puzzle index after saving new puzzles
    generate_puzzle_index()

if __name__ == "__main__":
    main()
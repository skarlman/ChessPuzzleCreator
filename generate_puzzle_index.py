import json
from pathlib import Path

def generate_puzzle_index():
    puzzles_dir = Path("frontend/public/puzzles")
    puzzle_files = []
    games_map = {}
    
    # Collect all puzzle data
    for puzzle_file in puzzles_dir.glob("*.json"):
        if puzzle_file.name != "index.json":
            with open(puzzle_file) as f:
                try:
                    puzzle_data = json.load(f)
                    puzzle_id = puzzle_file.stem
                    game_id = str(puzzle_data["game"]["id"])  # Ensure game_id is a string
                    
                    print(f"Processing puzzle {puzzle_id} from game {game_id}")  # Debug print
                    
                    # Create game entry if not exists
                    if game_id not in games_map:
                        print(f"Adding new game {game_id}")  # Debug print
                        games_map[game_id] = {
                            "id": game_id,
                            "white": puzzle_data["game"]["white"],
                            "black": puzzle_data["game"]["black"],
                            "timestamp": puzzle_data["game"]["timestamp"],
                            "puzzles": []
                        }
                    
                    games_map[game_id]["puzzles"].append(puzzle_id)
                    puzzle_files.append(puzzle_id)
                except Exception as e:
                    print(f"Error processing {puzzle_file}: {e}")
    
    print(f"Found {len(games_map)} games")  # Debug print
    for game_id, game_data in games_map.items():
        print(f"Game {game_id}: {len(game_data['puzzles'])} puzzles")  # Debug print
    
    # Convert games map to sorted list
    games_list = list(games_map.values())
    games_list.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Create index with both puzzles and games
    index_data = {
        "puzzles": puzzle_files,
        "games": games_list
    }
    
    with open(puzzles_dir / "index.json", "w") as f:
        json.dump(index_data, f, indent=2)
    
    print(f"Generated index with {len(puzzle_files)} puzzles and {len(games_list)} games")  # Debug print

if __name__ == "__main__":
    generate_puzzle_index() 
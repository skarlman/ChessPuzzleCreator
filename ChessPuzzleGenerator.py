import json
import uuid
from pathlib import Path
import hashlib

import chess


class ChessPuzzleGenerator:
    def __init__(self, stockfish_path=r"C:\code\ChessPuzzleCreator\stockfish\stockfish-windows-x86-64-avx2"):
        self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
        # Configure Stockfish engine options
        self.engine.configure({
            "Threads": 16,              # Adjust based on your CPU cores (typically num_cores - 1)
            "Hash": 4096,              # Memory in MB for hash tables
            "UCI_LimitStrength": False,  # Don't limit engine strength
            "UCI_Elo": 3000,          # Maximum playing strength
            "Move Overhead": 10,      # Lower values can make engine respond faster
        })
        self.analysis_depth = 23
        self.missed_move_threshold = 150  # centipawns
        self.puzzles_dir = Path("frontend/public/puzzles")
        self.puzzles_dir.mkdir(parents=True, exist_ok=True)

    def analyze_position(self, board, depth=None):
        """Analyze a position using Stockfish."""
        if depth is None:
            depth = self.analysis_depth

        try:
            info = self.engine.analyse(board, chess.engine.Limit(depth=depth))
            # Ensure we have a principal variation
            if 'pv' not in info or not info['pv']:
                return {'score': info.get('score', None), 'pv': []}
            return info
        except Exception as e:
            print(f"Error analyzing position: {e}")
            return {'score': None, 'pv': []}

    def find_missed_tactics(self, game, player_username):
        """Find positions where any player (or specific player) missed tactical opportunities."""
        puzzles = []
        board = game.board()
        move_number = 1
        
        for move in game.mainline_moves():
            if player_username is None or (
                (board.turn == chess.WHITE and game.headers["White"] == player_username) or 
                (board.turn == chess.BLACK and game.headers["Black"] == player_username)
            ):
                current_position = board.fen()
                current_turn = 'white' if board.turn == chess.WHITE else 'black'
                
                # Look for missed tactics
                best_move_info = self.analyze_position(board)
                if 'pv' not in best_move_info or not best_move_info['pv']:
                    board.push(move)
                    continue

                best_move = best_move_info["pv"][0]
                best_eval = best_move_info["score"].white().score(mate_score=10000)
                
                # Make the actual move and analyze
                board.push(move)
                actual_pos_info = self.analyze_position(board)
                if 'score' not in actual_pos_info:
                    continue
                    
                actual_eval = actual_pos_info["score"].white().score(mate_score=10000)
                eval_diff = abs(best_eval - actual_eval)
                
                # Create puzzle if there's a significant mistake
                if eval_diff >= self.missed_move_threshold:
                    puzzle = {
                        "position": current_position,
                        "best_move": str(best_move),
                        "played_move": str(move),
                        "eval_diff": eval_diff,
                        "themes": ["mistake"],
                        "turn": current_turn,
                        "move_number": move_number
                    }
                    puzzles.append(puzzle)
            else:
                board.push(move)
            
            if board.turn == chess.WHITE:
                move_number += 1
        
        return puzzles

    def save_puzzle(self, puzzle, game_info):
        """Save puzzle to a JSON file with unique ID."""
        # Create a unique hash from the position and best move
        puzzle_hash = f"{puzzle['position']}_{puzzle['best_move']}"
        puzzle_id = hashlib.md5(puzzle_hash.encode()).hexdigest()

        # Extract game ID from URL for both chess.com and lichess
        game_url = game_info.get("url", "")
        if "chess.com" in game_url:
            game_id = game_url.split("/")[-1]
            # Convert move number to ply (each player's move counts as one)
            move_number = puzzle.get("move_number", 0)
            ply = (move_number - 1) * 2 -1
            if puzzle.get('turn') == 'black':
                ply += 1
            # Convert game URL to analysis URL with move
            game_url = game_url.replace("/game/", "/analysis/game/")
            game_url = f"{game_url}?tab=analysis&move={ply}"
        elif "lichess.org" in game_url:
            game_id = game_url.split("/")[-1]
            # For Lichess, keep the original URL as it handles move numbers differently
        else:
            # Fallback to provided ID or generate one if missing
            game_id = str(game_info.get("id", "")) or hashlib.md5(game_info.get("pgn", "").encode()).hexdigest()

        # Ensure game_info has the correct structure
        game_data = {
            "id": game_id,  # Use extracted or generated game ID
            "white": game_info.get("white", {}).get("username", game_info.get("white", "")),
            "black": game_info.get("black", {}).get("username", game_info.get("black", "")),
            "timestamp": game_info.get("end_time", ""),
            "url": game_url,
            "pgn": game_info.get("pgn", ""),
            "move_number": puzzle.get("move_number", 0)
        }

        puzzle_data = {
            "id": puzzle_id,
            "position": puzzle["position"],
            "best_move": str(puzzle["best_move"]),
            "played_move": str(puzzle["played_move"]),
            "eval_diff": puzzle["eval_diff"],
            "themes": puzzle["themes"],
            "turn_color": puzzle.get("turn", "white"),
            "turn_player": game_data["white"] if puzzle.get("turn") == "white" else game_data["black"],
            "game": game_data
        }

        puzzle_file = self.puzzles_dir / f"{puzzle_id}.json"
        with open(puzzle_file, 'w') as f:
            json.dump(puzzle_data, f, indent=2)
        return puzzle_id

    def close(self):
        """Clean up engine resources."""
        self.engine.quit()

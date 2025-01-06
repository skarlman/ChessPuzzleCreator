import requests
import json
import os
from datetime import datetime, timedelta
import time
from dateutil.relativedelta import relativedelta

class ChessComAPI:
    BASE_URL = "https://api.chess.com/pub"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    @staticmethod
    def get_player_games(username, cache_dir="games"):
        """Get all games for a player from the last 6 months."""
        # Create cache directory if it doesn't exist
        player_cache_dir = os.path.join(cache_dir, username)
        os.makedirs(player_cache_dir, exist_ok=True)
        
        all_games = []
        now = datetime.now()
        
        # Calculate date range
        end_date = datetime(now.year, now.month, 1)  # First of current month
        start_date = end_date - relativedelta(months=6)  # 6 months ago
        
        # Generate list of months to fetch
        current_date = end_date
        months_to_fetch = []
        while current_date >= start_date:
            months_to_fetch.append(current_date)
            current_date = current_date - relativedelta(months=1)
        
        # Fetch games for each month
        for date in months_to_fetch:
            year = date.year
            month = str(date.month).zfill(2)
            month_str = f"{year}/{month}"
            
            cache_file = os.path.join(player_cache_dir, f"{year}_{month}.json")
            
            # Check if we have cached data less than 24 hours old
            if os.path.exists(cache_file):
                file_age = time.time() - os.path.getmtime(cache_file)
                if file_age < 24 * 3600:  # 24 hours in seconds
                    print(f"Using cached data for {month_str}")
                    with open(cache_file, 'r') as f:
                        month_games = json.load(f)
                        all_games.extend(month_games)
                    continue
            
            # Fetch new data from API
            endpoint = f"{ChessComAPI.BASE_URL}/player/{username}/games/{year}/{month}"
            try:
                print(f"Fetching games for {month_str}...")
                response = requests.get(endpoint, headers=ChessComAPI.HEADERS)
                response.raise_for_status()
                month_games = response.json().get('games', [])
                
                # Cache the results
                with open(cache_file, 'w') as f:
                    json.dump(month_games, f)
                
                all_games.extend(month_games)
                
                # Respect API rate limits
                time.sleep(1)
                
            except Exception as e:
                print(f"Failed to fetch games for {month_str}: {str(e)}")
                # If we have cached data, use it even if it's old
                if os.path.exists(cache_file):
                    print(f"Using cached data for {month_str}")
                    with open(cache_file, 'r') as f:
                        month_games = json.load(f)
                        all_games.extend(month_games)
        
        return all_games

    @staticmethod
    def get_game(game_data):
        """Extract PGN from game data."""
        return game_data.get('pgn') 
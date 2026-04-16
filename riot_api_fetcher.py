import requests
import json
import os
from typing import Optional, List, Dict, Any
import time
from dotenv import load_dotenv

load_dotenv()

class RiotAPiFetcher:
    def __init__(self, api_key: str, data_dir: str = "data"):
        self.api_key = api_key
        self.base_url_eun1 = "https://eun1.api.riotgames.com"
        self.base_url_regional = "https://europe.api.riotgames.com"
        self.data_dir = data_dir

        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a request to Riot API with rate limit handling."""
        params = params or {}
        params['api_key'] = self.api_key

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get('Retry-After', 60))
                print(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after + 1)
                return self._make_request(url, {k: v for k, v in params.items() if k != 'api_key'})
            else:
                print(f"HTTP {e.response.status_code} error for {url}: {e.response.text}")
                return {}

    def get_players_by_rank(self, tier: str = "BRONZE", rank: str = "II",
                           num_players: int = 205,
                           queue: str = "RANKED_SOLO_5x5") -> List[Dict]:
        """Fetch up to num_players from a specific rank, paginating as needed."""
        url = f"{self.base_url_eun1}/lol/league/v4/entries/{queue}/{tier}/{rank}"

        print(f"Fetching players from {tier} {rank}...")
        players = []
        page = 1

        while len(players) < num_players:
            response = self._make_request(url, {'page': page})

            if not isinstance(response, list) or len(response) == 0:
                break

            players.extend(response)
            print(f"  Page {page}: {len(response)} players (total: {len(players)})")
            page += 1
            time.sleep(1.2)

        players = players[:num_players]
        print(f"Total players fetched: {len(players)}")
        return players

    def get_match_timeline(self, match_id: str) -> Dict[str, Any]:
        """Fetch detailed match timeline data including ward and vision events."""
        url = f"{self.base_url_regional}/lol/match/v5/matches/{match_id}/timeline"

        print(f"  Fetching timeline for match {match_id}...")
        return self._make_request(url)

    def get_match_data(self, match_id: str) -> Dict[str, Any]:
        """Fetch match data."""
        url = f"{self.base_url_regional}/lol/match/v5/matches/{match_id}"

        print(f"  Fetching match data {match_id}...")
        return self._make_request(url)

    def get_player_matches(self, puuid: str, start: int = 0, count: int = 1,
                           start_time: Optional[int] = None,
                           end_time: Optional[int] = None) -> List[str]:
        """Fetch recent match IDs for a player within optional time range."""
        url = f"{self.base_url_regional}/lol/match/v5/matches/by-puuid/{puuid}/ids"

        params: Dict[str, Any] = {'start': start, 'count': count, 'queue': 420}
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        print(f"  Fetching match history...")
        matches = self._make_request(url, params)

        if isinstance(matches, list):
            return matches
        return []

    def extract_vision_data(self, timeline: Dict) -> Dict[str, Any]:
        """Extract vision-related events from timeline (wards, vision score, etc)."""
        vision_data = {
            'ward_placed': [],
            'ward_killed': [],
            'vision_score': {},
            'stealth_ward_placed': [],
            'control_ward_purchased': [],
            'sight_ward_purchased': [],
            'trinket_updates': []
        }

        if 'info' not in timeline or 'frames' not in timeline['info']:
            return vision_data

        # Extract from timeline events
        for frame in timeline['info']['frames']:
            if 'events' in frame:
                for event in frame['events']:
                    event_type = event.get('type', '')

                    if event_type == 'WARD_PLACED':
                        vision_data['ward_placed'].append({
                            'timestamp': event.get('timestamp'),
                            'creator_id': event.get('creatorId'),
                            'ward_type': event.get('wardType'),
                            'x': event.get('x'),
                            'y': event.get('y')
                        })

                    elif event_type == 'WARD_KILL':
                        vision_data['ward_killed'].append({
                            'timestamp': event.get('timestamp'),
                            'killer_id': event.get('killerId'),
                            'ward_type': event.get('wardType'),
                            'x': event.get('x'),
                            'y': event.get('y')
                        })

                    elif event_type == 'ITEM_PURCHASED':
                        item_id = event.get('itemId')
                        if item_id == 2055:  # Control Ward
                            vision_data['control_ward_purchased'].append({
                                'timestamp': event.get('timestamp'),
                                'participant_id': event.get('participantId')
                            })

                    elif event_type == 'ITEM_SOLD' or event_type == 'ITEM_DESTROYED':
                        pass

            # Extract participant vision scores from frame participant lists
            if frame.get('participantFrames'):
                for participant_id, participant in frame['participantFrames'].items():
                    if 'visionScore' in participant:
                        if participant_id not in vision_data['vision_score']:
                            vision_data['vision_score'][participant_id] = []

                        vision_data['vision_score'][participant_id].append({
                            'timestamp': frame.get('timestamp'),
                            'vision_score': participant['visionScore']
                        })

        return vision_data

    def fetch_and_save_player_matches(self, num_players: int = 5, tier: str = "BRONZE",
                                      rank: str = "II",
                                      start_time: Optional[int] = None,
                                      end_time: Optional[int] = None):
        """
        Fetch N players from a rank and save one recent match for each.

        Args:
            num_players: Number of players to fetch
            tier: Tier (BRONZE, SILVER, GOLD, etc)
            rank: Rank (I, II, III, IV)
            start_time: Unix timestamp in seconds (optional)
            end_time: Unix timestamp in seconds (optional)
        """
        players = self.get_players_by_rank(tier, rank, num_players=num_players)

        print(f"\nProcessing {len(players)} players...")

        for idx, player in enumerate(players, 1):
            puuid = player.get('puuid')
            player_label = puuid[:16] if puuid else f"player_{idx}"

            print(f"\n[{idx}/{len(players)}] Processing {player_label}...")

            if not puuid:
                print(f"  No PUUID in player data, skipping")
                continue

            matches = self.get_player_matches(puuid, start=0, count=1,
                                              start_time=start_time, end_time=end_time)

            if not matches:
                print(f"  No matches found")
                continue

            match_id = matches[0]

            # Fetch full match data and timeline
            match_data = self.get_match_data(match_id)
            timeline = self.get_match_timeline(match_id)

            if not match_data:
                print(f"  Failed to fetch match data")
                continue

            # Extract vision data
            vision_data = self.extract_vision_data(timeline)

            # Prepare comprehensive output
            output = {
                'player_info': {
                    'puuid': puuid,
                    'tier': player['tier'],
                    'rank': player['rank'],
                    'league_points': player['leaguePoints'],
                    'wins': player['wins'],
                    'losses': player['losses']
                },
                'match_info': {
                    'match_id': match_id,
                    'game_duration': match_data.get('info', {}).get('gameDuration'),
                    'game_version': match_data.get('info', {}).get('gameVersion'),
                    'queue_id': match_data.get('info', {}).get('queueId'),
                    'timestamp': match_data.get('info', {}).get('gameStartTimestamp')
                },
                'match_data': match_data,
                'timeline': timeline,
                'vision_data': vision_data
            }

            # Save to file
            filename = f"{self.data_dir}/{puuid[:16]}_{match_id}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            print(f"  Saved to {filename}")

            # Rate limiting between requests
            time.sleep(1.2)

def load_config(path: str = "config.json") -> Dict[str, Any]:
    with open(path, 'r') as f:
        return json.load(f)

def main():
    import datetime

    API_KEY = os.getenv('RIOT_API_KEY')
    if not API_KEY:
        print("Error: RIOT_API_KEY not found in .env file")
        print("Create a .env file based on .env.example")
        return

    config = load_config()

    num_players = config['num_players']
    tier        = config['tier'].upper()
    rank        = config['rank'].upper()
    output_dir  = config['output_dir']
    start_date  = datetime.date.fromisoformat(config['start_date'])
    end_date    = datetime.date.fromisoformat(config['end_date'])

    start_time = int(datetime.datetime(start_date.year, start_date.month, start_date.day,
                                       tzinfo=datetime.timezone.utc).timestamp())
    end_time   = int(datetime.datetime(end_date.year, end_date.month, end_date.day,
                                       23, 59, 59, tzinfo=datetime.timezone.utc).timestamp())

    print(f"Config loaded:")
    print(f"  Players : {num_players}")
    print(f"  Division: {tier} {rank}")
    print(f"  Period  : {start_date} – {end_date}")
    print(f"  Output  : {output_dir}/")

    fetcher = RiotAPiFetcher(API_KEY, data_dir=output_dir)
    fetcher.fetch_and_save_player_matches(
        num_players=num_players,
        tier=tier,
        rank=rank,
        start_time=start_time,
        end_time=end_time
    )

    print(f"\nDone! Data saved to '{output_dir}/' folder")

if __name__ == "__main__":
    main()

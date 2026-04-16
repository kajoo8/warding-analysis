import requests
import json
import os
from typing import Optional, List, Dict, Any
import time
from dotenv import load_dotenv

load_dotenv()

class RiotAPiFetcher:
    def __init__(self, api_key: str):
        """Initialize the Riot API fetcher with your API key."""
        self.api_key = api_key
        self.base_url_americas = "https://americas.api.riotgames.com"
        self.base_url_eu = "https://euw1.api.riotgames.com"
        self.data_dir = "data"

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
                print(f"Error: {e}")
                return {}

    def get_players_by_rank(self, tier: str = "BRONZE", rank: str = "II",
                           division: int = 1, queue: str = "RANKED_SOLO_5x5") -> List[Dict]:
        """
        Fetch players from a specific rank.

        Args:
            tier: IRON, BRONZE, SILVER, GOLD, PLATINUM, DIAMOND, MASTER, GRANDMASTER, CHALLENGER
            rank: I, II, III, IV
            division: Page number (1-based)
            queue: RANKED_SOLO_5x5, RANKED_FLEX_SR, RANKED_FLEX_TT

        Returns:
            List of player objects
        """
        url = f"{self.base_url_eu}/lol/league/v4/entries/{queue}/{tier}/{rank}"

        print(f"Fetching players from {tier} {rank}...")
        players = []

        # Get up to 205 players (max per page is 205)
        response = self._make_request(url, {'page': division})

        if isinstance(response, list):
            players = response
            print(f"Found {len(players)} players")
        else:
            print(f"Unexpected response format")

        return players

    def get_match_timeline(self, match_id: str) -> Dict[str, Any]:
        """Fetch detailed match timeline data including ward and vision events."""
        url = f"{self.base_url_americas}/lol/match/v5/matches/{match_id}/timeline"

        print(f"  Fetching timeline for match {match_id}...")
        timeline = self._make_request(url)

        return timeline

    def get_match_data(self, match_id: str) -> Dict[str, Any]:
        """Fetch match data."""
        url = f"{self.base_url_americas}/lol/match/v5/matches/{match_id}"

        print(f"  Fetching match data {match_id}...")
        match_data = self._make_request(url)

        return match_data

    def get_player_matches(self, puuid: str, start: int = 0, count: int = 1) -> List[str]:
        """Fetch recent match IDs for a player."""
        url = f"{self.base_url_americas}/lol/match/v5/matches/by-puuid/{puuid}/ids"

        print(f" Fetching match history...")
        matches = self._make_request(url, {'start': start, 'count': count})

        return matches if isinstance(matches, list) else []

    def get_puuid_from_summoner(self, summoner_id: str) -> Optional[str]:
        """Get PUUID from summoner ID."""
        url = f"{self.base_url_eu}/lol/summoner/v4/summoners/{summoner_id}"

        summoner = self._make_request(url)
        return summoner.get('puuid') if summoner else None

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
            if 'participantFrames' in frame:
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
                                      rank: str = "II"):
        """
        Fetch N players from a rank and save one recent match for each.

        Args:
            num_players: Number of players to fetch
            tier: Tier (BRONZE, SILVER, GOLD, etc)
            rank: Rank (I, II, III, IV)
        """
        players = self.get_players_by_rank(tier, rank)
        players = players[:num_players]

        print(f"\nProcessing {len(players)} players...")

        for idx, player in enumerate(players, 1):
            print(f"\n[{idx}/{len(players)}] Processing {player['summonerName']}")

            summoner_id = player['summonerId']
            puuid = self.get_puuid_from_summoner(summoner_id)

            if not puuid:
                print(f"  Could not get PUUID for {player['summonerName']}")
                continue

            # Get recent matches
            matches = self.get_player_matches(puuid, start=0, count=1)

            if not matches:
                print(f"  No matches found for {player['summonerName']}")
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
                    'summoner_name': player['summonerName'],
                    'summoner_id': summoner_id,
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
            filename = f"{self.data_dir}/{player['summonerName'].replace(' ', '_')}_{match_id}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            print(f"  Saved to {filename}")

            # Rate limiting between requests
            time.sleep(1.2)

def main():
    """Main entry point."""
    API_KEY = os.getenv('RIOT_API_KEY')

    if not API_KEY:
        print("Error: RIOT_API_KEY not found in .env file")
        print("Please create a .env file with your API key. See .env.example for reference.")
        return

    fetcher = RiotAPiFetcher(API_KEY)

    # Customize these parameters
    num_players = int(input("How many players to fetch? (default: 5): ") or "5")
    tier = input("Enter tier (BRONZE, SILVER, GOLD, PLATINUM, DIAMOND): ") or "BRONZE"
    rank = input("Enter rank (I, II, III, IV): ") or "II"

    print(f"\nFetching {num_players} players from {tier} {rank}...")

    fetcher.fetch_and_save_player_matches(
        num_players=num_players,
        tier=tier.upper(),
        rank=rank.upper()
    )

    print(f"\n✓ Complete! Data saved to '{fetcher.data_dir}' folder")

if __name__ == "__main__":
    main()

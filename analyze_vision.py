import json
import os
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

class VisionAnalyzer:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir

    def load_all_matches(self) -> List[Dict[str, Any]]:
        """Load all match data from data directory."""
        matches = []

        if not os.path.exists(self.data_dir):
            print(f"Directory {self.data_dir} not found")
            return matches

        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.data_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        matches.append(data)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")

        return matches

    def analyze_ward_statistics(self, matches: List[Dict]) -> Dict[str, Any]:
        """Analyze ward placement and kills statistics."""
        stats = {
            'total_wards_placed': 0,
            'total_wards_killed': 0,
            'wards_per_player': defaultdict(lambda: {'placed': 0, 'killed': 0}),
            'ward_types': defaultdict(int),
            'avg_wards_per_match': 0,
            'avg_kills_per_match': 0
        }

        for match in matches:
            vision_data = match.get('vision_data', {})

            # Count wards placed
            for ward in vision_data.get('ward_placed', []):
                stats['total_wards_placed'] += 1
                creator_id = ward.get('creator_id')
                if creator_id:
                    stats['wards_per_player'][creator_id]['placed'] += 1

                ward_type = ward.get('ward_type', 'unknown')
                stats['ward_types'][ward_type] += 1

            # Count wards killed
            for ward in vision_data.get('ward_killed', []):
                stats['total_wards_killed'] += 1
                killer_id = ward.get('killer_id')
                if killer_id:
                    stats['wards_per_player'][killer_id]['killed'] += 1

        num_matches = len(matches)
        if num_matches > 0:
            stats['avg_wards_per_match'] = stats['total_wards_placed'] / num_matches
            stats['avg_kills_per_match'] = stats['total_wards_killed'] / num_matches

        return stats

    def analyze_vision_score(self, matches: List[Dict]) -> Dict[str, Any]:
        """Analyze vision score statistics."""
        stats = {
            'avg_vision_score_by_match': [],
            'players_with_vision_data': set(),
            'vision_score_progression': defaultdict(list)
        }

        for match in matches:
            vision_data = match.get('vision_data', {})
            vision_scores = vision_data.get('vision_score', {})

            match_avg_vision = 0
            count = 0

            for participant_id, scores in vision_scores.items():
                stats['players_with_vision_data'].add(int(participant_id))

                if scores:
                    final_score = scores[-1].get('vision_score', 0)
                    match_avg_vision += final_score
                    count += 1

                    # Track vision score progression
                    stats['vision_score_progression'][int(participant_id)].extend(
                        [s.get('vision_score', 0) for s in scores]
                    )

            if count > 0:
                stats['avg_vision_score_by_match'].append(match_avg_vision / count)

        return stats

    def print_summary(self, matches: List[Dict]):
        """Print analysis summary."""
        if not matches:
            print("No matches found to analyze")
            return

        print(f"\n{'='*60}")
        print(f"ANALIZA DANYCH - {len(matches)} MECZY")
        print(f"{'='*60}\n")

        # Ward statistics
        ward_stats = self.analyze_ward_statistics(matches)
        print("STATYSTYKI WARDÓW:")
        print(f"  Całkowicie postaw onych wardów: {ward_stats['total_wards_placed']}")
        print(f"  Całkowicie zniszczonych wardów: {ward_stats['total_wards_killed']}")
        print(f"  Średnio wardów na mecz: {ward_stats['avg_wards_per_match']:.1f}")
        print(f"  Średnio zniszczonych na mecz: {ward_stats['avg_kills_per_match']:.1f}")

        if ward_stats['ward_types']:
            print(f"\n  Typy wardów:")
            for ward_type, count in ward_stats['ward_types'].items():
                print(f"    {ward_type}: {count}")

        # Vision score
        vision_stats = self.analyze_vision_score(matches)
        print(f"\nSTATYSTYKI VISIONU:")
        print(f"  Gracze z danymi visionu: {len(vision_stats['players_with_vision_data'])}")

        if vision_stats['avg_vision_score_by_match']:
            avg = sum(vision_stats['avg_vision_score_by_match']) / len(vision_stats['avg_vision_score_by_match'])
            print(f"  Średni vision score na gracza na mecz: {avg:.1f}")

        # Match info
        print(f"\nINFORMACJE O MECZACH:")
        total_duration = 0
        for match in matches:
            duration = match.get('match_info', {}).get('game_duration', 0)
            total_duration += duration

        if matches:
            avg_duration = total_duration / len(matches)
            print(f"  Średni czas trwania meczu: {int(avg_duration / 60)} minut")

        print(f"\n{'='*60}\n")

    def export_summary_json(self, filename: str = "vision_summary.json"):
        """Export analysis summary to JSON."""
        matches = self.load_all_matches()
        summary = {
            'total_matches': len(matches),
            'ward_statistics': self.analyze_ward_statistics(matches),
            'vision_statistics': self.analyze_vision_score(matches),
            'matches': [
                {
                    'player': m.get('player_info', {}).get('summoner_name'),
                    'match_id': m.get('match_info', {}).get('match_id'),
                    'wards_placed': len(m.get('vision_data', {}).get('ward_placed', [])),
                    'wards_killed': len(m.get('vision_data', {}).get('ward_killed', []))
                }
                for m in matches
            ]
        }

        # Convert defaultdicts and sets to JSON-serializable format
        summary['ward_statistics']['wards_per_player'] = dict(summary['ward_statistics']['wards_per_player'])
        summary['ward_statistics']['ward_types'] = dict(summary['ward_statistics']['ward_types'])

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"Summary saved to {filename}")

def main():
    analyzer = VisionAnalyzer()
    matches = analyzer.load_all_matches()

    if matches:
        analyzer.print_summary(matches)
        analyzer.export_summary_json()
    else:
        print("Brak danych do analizy. Najpierw uruchom riot_api_fetcher.py")

if __name__ == "__main__":
    main()

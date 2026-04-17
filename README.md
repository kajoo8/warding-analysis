# LOL-Wards: Vision Metric Analysis Across League of Legends Seasons

A data pipeline and statistical analysis project investigating whether warding behavior changed between Season 2025 and Season 2026 in League of Legends ranked play. The central hypothesis is that new jungle terrain introduced in Season 2026 ("fairy spots") lowers the physical barrier to warding, causing measurable increases in vision metrics.

---

## Hypothesis

> Players in Season 2026 place significantly more wards and achieve higher vision scores than players at equivalent rank in Season 2025, due to new accessible warding positions introduced with the Season 2026 jungle rework.

---

## Results Summary

Statistical comparisons (Mann-Whitney U, non-parametric) across two rank tiers:

| Metric | Bronze I | Emerald I |
|---|---|---|
| Vision Score per Minute | +35% ** | +21% ** |
| Stealth Wards Placed | +14% ** | +5% ** |
| Total Wards Placed | +14% ** | +5% ** |
| Wards Killed | +25% ** | +10% ** |
| Control Wards Placed | ** | n.s. |
| Vision Wards Bought | ** | n.s. |

`**` = statistically significant (p < 0.05), `n.s.` = not significant

6/7 features show significant increases in Emerald I; 7/7 in Bronze I.

---

## Repository Structure

```
warding-analysis/
├── data/
│   ├── season2025/
│   │   ├── bronze1/          # ~423 matches (~4,230 participants)
│   │   └── emerald1/         # ~500 matches (~5,000 participants)
│   └── season2026/
│       ├── bronze1/          # ~530 matches (~5,300 participants)
│       └── emerald1/         # ~534 matches (~5,340 participants)
├── figures/
│   ├── distributions.png
│   ├── boxplots.png
│   └── mean_comparison.png
├── vision_analysis.ipynb     # Statistical analysis notebook
├── riot_api_fetcher.py       # Riot API data collection pipeline
├── trim_data.py              # JSON size reduction utility
├── config.example.json       # Configuration template
├── .env.example              # Environment variable template
└── requirements.txt
```

---

## Setup

**Requirements:** Python 3.9+, a [Riot Games API key](https://developer.riotgames.com/)

```bash
git clone https://github.com/kajoo8/warding-analysis
cd warding-analysis
pip install -r requirements.txt
cp .env.example .env           # then set RIOT_API_KEY=<your key>
cp config.example.json config.json  # then set tier, rank, date range, num_players
```

---

## Usage

### 1. Collect Match Data

```bash
python riot_api_fetcher.py
```

Fetches ranked players for the configured tier/rank, retrieves their recent match IDs, downloads full match data and timelines from the Riot API (EUW), and extracts vision-related events. Output is written to `data/<season>/<tier>/` as JSON files, one per match.

The fetcher respects Riot API rate limits with automatic backoff and retry on 429 responses.

### 2. Trim JSON Files (Optional)

```bash
python trim_data.py data/
```

Strips non-vision fields from match JSON files to reduce disk usage. Reports compression ratio per folder. Safe to run multiple times (idempotent).

### 3. Run Statistical Analysis

```bash
jupyter notebook vision_analysis.ipynb
```

The notebook:
1. Loads all participant records from the four data groups (2 seasons × 2 ranks)
2. Tests for normality using Shapiro-Wilk and D'Agostino-Pearson tests
3. Compares groups with Mann-Whitney U (non-parametric, appropriate for non-normal distributions)
4. Computes effect sizes via rank-biserial correlation
5. Outputs figures to `figures/`

---

## Vision Features Analyzed

| Feature | Description |
|---|---|
| `visionScorePerMinute` | Vision score normalized by game length |
| `visionScore` | Raw end-of-game vision score |
| `stealthWardsPlaced` | Yellow trinket ward placements |
| `controlWardsPlaced` | Pink ward placements |
| `visionWardsBoughtInGame` | Control ward purchases |
| `wardsPlaced` | Total wards placed |
| `wardsKilled` | Enemy wards destroyed |

---

## Configuration

`config.json` controls data collection:

```json
{
  "output_dir": "data",
  "num_players": 1000,
  "tier": "BRONZE",
  "rank": "I",
  "start_date": "2026-02-01",
  "end_date": "2026-03-31"
}
```

Run the fetcher once per group (season × rank combination), updating `start_date`, `end_date`, and `output_dir` each time.

---

## Data Source

[Riot Games API](https://developer.riotgames.com/) — EUNE server, ranked solo/duo queue. Data collection is subject to Riot's API rate limits (20 requests/second, 100 requests/2 minutes on development keys).

*This project is not affiliated with or endorsed by Riot Games.*

---
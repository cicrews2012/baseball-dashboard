#!/usr/bin/env python3
"""
Fetches the current year's MLB Top 100 prospects from MLB's Stats API and
writes data/prospects-{year}.json in the schema the dashboard actually reads.

Note: MLB's Stats API prospects endpoint does not include FanGraphs "The
Board" FV (Future Value) grades, risk levels, or minor-league level detail
the way the manually-curated historical years (2020-2025) do. This script's
`notes` field is just "MLB Pipeline Top 100 - Rank #N" as a result, so the
FV filter and notes column will look sparser on days this automation writes
than on days the data is manually curated from FanGraphs. That's expected,
not a bug.

This script only ever writes the current (or, on fallback, most recent
non-historical) year's file - it refuses to touch 2020-2025, which are
frozen, manually-curated snapshots.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'

# Manually-curated, FanGraphs-sourced historical years this script must never overwrite.
PROTECTED_YEARS = {'2020', '2021', '2022', '2023', '2024', '2025'}


def fetch_prospects_from_api(year):
    """
    Fetch prospects using MLB Stats API.
    Returns: list of prospect dicts, or None if not available
    """
    print(f"Fetching {year} prospects from MLB Stats API...")

    try:
        url = f"https://statsapi.mlb.com/api/v1/prospects?year={year}&limit=100"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        if 'prospects' not in data or not data['prospects']:
            print(f"No prospects data in API response for {year}")
            return None

        prospects = []
        for idx, prospect in enumerate(data['prospects'], 1):
            person = prospect.get('person', {})

            name = person.get('fullName', 'Unknown')
            position = person.get('primaryPosition', {}).get('abbreviation', 'OF')

            team_data = prospect.get('team', {})
            team = team_data.get('abbreviation', 'N/A')

            birth_date = person.get('birthDate')
            age = calculate_age(birth_date) if birth_date else None

            # Coarse tier based on rank alone - no FV grade available from this source
            if idx <= 10:
                tier = 'Elite'
            elif idx <= 30:
                tier = 'Star'
            elif idx <= 60:
                tier = 'Solid'
            else:
                tier = 'Prospect'

            prospects.append({
                'rank': idx,
                'name': name,
                'team': team or 'N/A',
                'pos': position or 'OF',
                'tier': tier,
                'age': age if age is not None else 20,
                'eta': str(year),
                'notes': f'MLB Pipeline Top 100 · Rank #{idx}',
            })

        print(f"Fetched {len(prospects)} prospects from API")
        return prospects

    except requests.RequestException as e:
        print(f"API request failed: {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"Error parsing API response: {e}")
        return None


def calculate_age(birth_date_str):
    """Calculate age from birth date string (YYYY-MM-DD)"""
    try:
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d')
        today = datetime.now()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except (ValueError, TypeError):
        return None


def should_fetch_current_year(year):
    """
    Determine if we should try fetching the current year.
    MLB releases Top 100 around Jan 23 each year.
    """
    now = datetime.now()
    current_year = now.year

    if int(year) == current_year and now.month == 1 and now.day < 24:
        print(f"{year} Top 100 not released yet (releases ~Jan 23)")
        return False

    return True


def main():
    """Main fetcher logic with smart year fallback, guarded against touching historical data."""

    current_year = datetime.now().year
    requested_year = sys.argv[1] if len(sys.argv) > 1 else str(current_year)

    if requested_year in PROTECTED_YEARS:
        print(f"Refusing to fetch {requested_year}: that's a manually-curated FanGraphs "
              f"historical year, not something this script may overwrite.")
        return 1

    print(f"MLB Prospects Fetcher - Requested Year: {requested_year}")
    print("=" * 60)

    prospects = None
    final_year = requested_year

    if should_fetch_current_year(requested_year):
        prospects = fetch_prospects_from_api(requested_year)

    if not prospects:
        fallback_year = str(int(requested_year) - 1)
        if fallback_year in PROTECTED_YEARS:
            print(f"No data for {requested_year}, and fallback year {fallback_year} is a "
                  f"protected historical year - not falling back into it.")
        else:
            print(f"Falling back to {fallback_year} data...")
            prospects = fetch_prospects_from_api(fallback_year)
            final_year = fallback_year if prospects else requested_year

    if not prospects:
        print(f"FAILED: Could not fetch prospects for {requested_year} or an eligible fallback year")
        return 1

    if final_year in PROTECTED_YEARS:
        print(f"Refusing to write {final_year}: manually-curated FanGraphs historical data.")
        return 1

    DATA_DIR.mkdir(exist_ok=True)
    output_file = DATA_DIR / f'prospects-{final_year}.json'

    output_data = {
        'source': 'MLB Stats API',
        'year': final_year,
        'lastUpdated': datetime.now(timezone.utc).isoformat(),
        'totalProspects': len(prospects),
        'prospects': prospects,
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print("SUCCESS!")
    print(f"Saved {len(prospects)} prospects to: {output_file}")
    print(f"Year: {final_year}")
    print(f"Updated: {output_data['lastUpdated']}")

    return 0


if __name__ == '__main__':
    sys.exit(main())

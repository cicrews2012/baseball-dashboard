#!/usr/bin/env python3
"""
MLB Prospects Fetcher using Stats API
Fetches Top 100 prospects from MLB's Stats API
Falls back to previous year if current year not released yet
"""

import json
import sys
from datetime import datetime
from pathlib import Path
import requests


def fetch_prospects_from_api(year):
    """
    Fetch prospects using MLB Stats API
    Returns: list of prospect dicts, or None if not available
    """
    print(f"🌐 Fetching {year} prospects from MLB Stats API...")
    
    try:
        # MLB Stats API endpoint for prospects
        url = f"https://statsapi.mlb.com/api/v1/prospects?year={year}&limit=100"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if 'prospects' not in data or not data['prospects']:
            print(f"⚠️ No prospects data in API response for {year}")
            return None
        
        prospects = []
        for idx, prospect in enumerate(data['prospects'], 1):
            # Extract player info
            person = prospect.get('person', {})
            
            name = person.get('fullName', 'Unknown')
            player_id = person.get('id', 0)
            
            # Position
            position = person.get('primaryPosition', {}).get('abbreviation', 'OF')
            
            # Team
            team_data = prospect.get('team', {})
            team = team_data.get('abbreviation', 'N/A')
            
            # Age
            birth_date = person.get('birthDate')
            age = calculate_age(birth_date) if birth_date else 20
            
            # Determine tier based on rank
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
                'pos': position or 'OF',
                'team': team or 'N/A',
                'age': age,
                'eta': year,
                'tier': tier,
                'notes': f'{year} prospect via MLB Pipeline',
                'mlb_id': player_id
            })
        
        print(f"✅ Successfully fetched {len(prospects)} prospects from API")
        return prospects
        
    except requests.RequestException as e:
        print(f"❌ API request failed: {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"❌ Error parsing API response: {e}")
        return None


def calculate_age(birth_date_str):
    """Calculate age from birth date string (YYYY-MM-DD)"""
    try:
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d')
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except:
        return 20


def should_fetch_current_year(year):
    """
    Determine if we should try fetching the current year
    MLB releases Top 100 around Jan 23 each year
    """
    now = datetime.now()
    current_year = now.year
    
    # If requesting current year and it's before Jan 24
    if int(year) == current_year and now.month == 1 and now.day < 24:
        print(f"⏰ {year} Top 100 not released yet (releases ~Jan 23)")
        return False
    
    return True


def main():
    """Main fetcher logic with smart year fallback"""
    
    # Determine year to fetch (default to current year)
    current_year = datetime.now().year
    requested_year = sys.argv[1] if len(sys.argv) > 1 else str(current_year)
    
    print(f"🎯 MLB Prospects Fetcher - Requested Year: {requested_year}")
    print("="*60)
    
    prospects = None
    final_year = requested_year
    
    # Try requested year first (if it should be available)
    if should_fetch_current_year(requested_year):
        prospects = fetch_prospects_from_api(requested_year)
    
    # If failed or not available, try previous year
    if not prospects:
        fallback_year = str(int(requested_year) - 1)
        print(f"\n💡 Falling back to {fallback_year} data...")
        prospects = fetch_prospects_from_api(fallback_year)
        final_year = fallback_year if prospects else requested_year
    
    # Save results
    if prospects:
        # Create data directory if needed
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        
        # Save to file
        output_file = data_dir / f'prospects_{final_year}.json'
        
        output_data = {
            'year': final_year,
            'last_updated': datetime.now().isoformat(),
            'source': 'MLB Stats API',
            'count': len(prospects),
            'prospects': prospects
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n✅ SUCCESS!")
        print(f"📁 Saved {len(prospects)} prospects to: {output_file}")
        print(f"📅 Year: {final_year}")
        print(f"🕐 Updated: {output_data['last_updated']}")
        
        # Also save a "latest" file for easy loading
        latest_file = data_dir / 'prospects_latest.json'
        with open(latest_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"📁 Also saved to: {latest_file}")
        
        return 0
    else:
        print(f"\n❌ FAILED: Could not fetch prospects for {requested_year} or fallback years")
        return 1


if __name__ == '__main__':
    sys.exit(main())

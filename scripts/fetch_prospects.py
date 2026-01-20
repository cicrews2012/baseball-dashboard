#!/usr/bin/env python3
"""
MLB Prospects Scraper with Smart Year Fallback
Fetches Top 100 prospects from MLB.com
Falls back to previous year if current year not released yet
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup

def fetch_prospects(year):
    """
    Fetch prospects for a given year from MLB.com
    Returns: list of prospect dicts, or None if not available
    """
    print(f"🌐 Fetching {year} prospects from MLB.com...")
    
    # MLB Pipeline prospects URL
    url = f"https://www.mlb.com/prospects/{year}"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"✅ HTML fetched for {year}, parsing...")
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find prospects table or list
        # MLB.com structure may vary, try multiple selectors
        prospects = []
        
        # Method 1: Look for table
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')[1:]  # Skip header
            print(f"Found table with {len(rows)} rows")
            
            for idx, row in enumerate(rows, 1):
                cells = row.find_all('td')
                if len(cells) < 3:
                    continue
                
                # Extract player name (usually in a link)
                name_cell = cells[1] if len(cells) > 1 else cells[0]
                name_link = name_cell.find('a')
                name = name_link.text.strip() if name_link else name_cell.text.strip()
                
                # Clean name
                name = ' '.join(name.split())
                if not name or len(name) < 2:
                    continue
                
                # Try to extract team, position, age from other cells
                team = ''
                position = ''
                age = None
                
                for cell in cells:
                    text = cell.text.strip()
                    # Team (3-letter code)
                    if len(text) == 3 and text.isupper():
                        team = text
                    # Position
                    if text in ['C', '1B', '2B', '3B', 'SS', 'OF', 'LHP', 'RHP', 'P', 'DH']:
                        position = text
                    # Age
                    if text.isdigit() and 16 <= int(text) <= 35:
                        age = int(text)
                
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
                    'age': age or 20,
                    'eta': year,
                    'tier': tier,
                    'notes': f'{year} prospect via MLB Pipeline'
                })
        
        # Method 2: Look for prospect cards/divs (fallback)
        if not prospects:
            print("No table found, trying alternative selectors...")
            
            # Try to find any divs or articles with prospect/player data
            prospect_cards = soup.find_all(['div', 'article', 'li'])
            print(f"Found {len(prospect_cards)} potential elements, filtering for prospects...")
            
            rank = 1
            for card in prospect_cards:
                try:
                    # Look for player names in links or headings
                    name_elem = card.find(['a', 'h1', 'h2', 'h3', 'h4', 'span'], class_=lambda x: x and ('name' in str(x).lower() or 'player' in str(x).lower()))
                    
                    if not name_elem:
                        # Try finding any link that might be a player
                        name_elem = card.find('a', href=lambda x: x and '/player/' in str(x))
                    
                    if name_elem:
                        name = name_elem.get_text(strip=True)
                        
                        # Clean name and validate
                        name = ' '.join(name.split())
                        if len(name) < 3 or len(name) > 50:
                            continue
                        
                        # Skip if it's not a person's name (heuristic checks)
                        if any(skip in name.lower() for skip in ['news', 'video', 'stats', 'roster', 'schedule', 'more', 'mlb', 'prospects', 'rankings']):
                            continue
                        
                        # Try to extract team, position, age from the card
                        card_text = card.get_text()
                        
                        # Look for position codes
                        position = ''
                        for pos in ['RHP', 'LHP', 'C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'P']:
                            if pos in card_text:
                                position = pos
                                break
                        
                        # Look for team abbreviation (3 capital letters)
                        import re
                        team_match = re.search(r'\b([A-Z]{2,3})\b', card_text)
                        team = team_match.group(1) if team_match else ''
                        
                        # Look for age (2 digit number between 16-35)
                        age_match = re.search(r'\b(1[6-9]|2[0-9]|3[0-5])\b', card_text)
                        age = int(age_match.group(1)) if age_match else 20
                        
                        # Determine tier based on rank
                        if rank <= 10:
                            tier = 'Elite'
                        elif rank <= 30:
                            tier = 'Star'
                        elif rank <= 60:
                            tier = 'Solid'
                        else:
                            tier = 'Prospect'
                        
                        prospects.append({
                            'rank': rank,
                            'name': name,
                            'pos': position or 'OF',
                            'team': team or 'N/A',
                            'age': age,
                            'eta': year,
                            'tier': tier,
                            'notes': f'{year} prospect via MLB Pipeline'
                        })
                        
                        rank += 1
                        
                        # Stop at 100 prospects
                        if rank > 100:
                            break
                        
                except Exception as e:
                    continue
        
        if prospects:
            print(f"✅ Successfully parsed {len(prospects)} prospects for {year}")
            return prospects
        else:
            print(f"⚠️ No prospects found for {year}")
            return None
            
    except requests.RequestException as e:
        print(f"❌ Error fetching {year}: {e}")
        return None
    except Exception as e:
        print(f"❌ Error parsing {year}: {e}")
        return None


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
    """Main scraper logic with smart year fallback"""
    
    # Determine year to fetch (default to current year)
    current_year = datetime.now().year
    requested_year = sys.argv[1] if len(sys.argv) > 1 else str(current_year)
    
    print(f"🎯 MLB Prospects Scraper - Requested Year: {requested_year}")
    print("="*60)
    
    prospects = None
    final_year = requested_year
    
    # Try requested year first (if it should be available)
    if should_fetch_current_year(requested_year):
        prospects = fetch_prospects(requested_year)
    
    # If failed or not available, try previous year
    if not prospects:
        fallback_year = str(int(requested_year) - 1)
        print(f"\n💡 Falling back to {fallback_year} data...")
        prospects = fetch_prospects(fallback_year)
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
            'source': 'MLB.com Pipeline',
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

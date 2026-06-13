import requests
from bs4 import BeautifulSoup
import urllib3

# Suppress insecure request warnings for UTeM website
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def scrape_ftmk_staff():
    """
    Scrapes the FTMK staff directories using requests and returns a list of dictionaries
    containing lecturer profile information.
    """
    urls = [
        ('Software Engineering', 'https://ftmk.utem.edu.my/web/index.php/about/staff-directory/staff-directory-department-of-software-engineering-se/'),
        ('Interactive Media', 'https://ftmk.utem.edu.my/web/index.php/about/staff-directory/staff-directory-department-of-interactive-media-mi/'),
        ('Computer System & Comm', 'https://ftmk.utem.edu.my/web/index.php/about/staff-directory/staff-directory-department-of-computer-system-communication-2/'),
        ('Applied Data Engineering', 'https://ftmk.utem.edu.my/web/index.php/about/staff-directory/staff-directory-department-of-applied-data-engineering/'),
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    
    profiles = []
    
    for dept, url in urls:
        try:
            r = requests.get(url, headers=headers, verify=False, timeout=15)
            if r.status_code != 200:
                print(f"Failed to fetch {url}. Status: {r.status_code}")
                continue
                
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Find all table rows
            for row in soup.find_all('tr'):
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 4:
                    name_elem = cols[0]
                    title_elem = cols[1]
                    email_elem = cols[2]
                    block_elem = cols[3]
                    room_elem = cols[4] if len(cols) > 4 else None
                    
                    name = name_elem.get_text(separator=' ', strip=True)
                    # Clean up "Seconded to"
                    if '(' in name:
                        name = name.split('(')[0].strip()
                        
                    title = title_elem.get_text(strip=True)
                    email_prefix = email_elem.get_text(strip=True)
                    block = block_elem.get_text(strip=True)
                    room = room_elem.get_text(strip=True) if room_elem else ""
                    
                    # Ignore header row
                    if 'NAME' in name.upper() or not name:
                        continue
                        
                    # Filter out obvious non-names
                    if len(name) > 3 and email_prefix:
                        email = f"{email_prefix}@utem.edu.my" if not email_prefix.endswith('@utem.edu.my') else email_prefix
                        
                        profiles.append({
                            'name': name,
                            'title': title,
                            'email': email,
                            'department': dept,
                            'block': block,
                            'office_room': room
                        })
                        
        except Exception as e:
            print(f"Scraper error on {dept}: {e}")
            
    return profiles

if __name__ == '__main__':
    res = scrape_ftmk_staff()
    print(f"Scraped {len(res)} profiles.")
    if res:
        print(res[0])

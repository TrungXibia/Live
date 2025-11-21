import requests
from bs4 import BeautifulSoup
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

url = "https://www.minhngoc.net.vn/xo-so-truc-tiep/mien-bac.html"
try:
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
    soup = BeautifulSoup(r.content, 'html.parser')
    
    box = soup.find('div', class_='box_kqxs')
    if box:
        print("Found box_kqxs")
        # Check for my expected classes
        classes_to_check = ['giai-db', 'giai-nhat', 'giai-nhi', 'giai-ba', 'giai-tu', 'giai-nam', 'giai-sau', 'giai-bay']
        for cls in classes_to_check:
            found = box.find(class_=cls)
            if found:
                print(f"Found class '{cls}':")
                # Print the numbers found inside
                nums = [s.get_text(strip=True) for s in found.find_all('div') if s.get_text(strip=True).isdigit()]
                if not nums:
                     nums = [s.get_text(strip=True) for s in found.find_all(string=True) if s.get_text(strip=True).isdigit() and len(s.get_text(strip=True)) > 1]
                print(f"  -> Numbers: {nums}")
            else:
                print(f"NOT FOUND class '{cls}'")
                
        # If many not found, print all classes inside box to see what's there
        print("\nAll classes found in box:")
        all_classes = set()
        for tag in box.find_all(True):
            if tag.get('class'):
                for c in tag.get('class'):
                    all_classes.add(c)
        print(sorted(list(all_classes)))
            
    else:
        print("box_kqxs NOT FOUND")

except Exception as e:
    print(f"Error: {e}")

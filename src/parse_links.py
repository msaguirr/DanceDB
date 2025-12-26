import re
import csv
from bs4 import BeautifulSoup

INPUT_FILE = 'assets/dance_sheet.html'
OUTPUT_FILE = 'assets/copperknob_links_extracted.csv'

def get_last_line(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        return lines[-1] if lines else ''

def extract_links_and_context(html_line):
    soup = BeautifulSoup(html_line, 'html.parser')
    results = []
    def extract_copperknob_url(href):
        match = re.search(r'q=(https://www.copperknob.co.uk/[^&]+)', href)
        if match:
            return match.group(1)
        return href
    for a in soup.find_all('a', href=True):
        href = a['href']
        real_url = extract_copperknob_url(href)
        if 'copperknob.co.uk' in real_url:
            text = a.get_text(strip=True)
            parent = a.find_parent()
            row_data = []
            if parent and parent.name == 'td':
                tr = parent.find_parent('tr')
                if tr:
                    row_data = [td.get_text(strip=True) for td in tr.find_all('td')]
            if not row_data:
                row_data = [text]
            results.append({'url': real_url, 'row': row_data})
    return results

def write_to_csv(data, output_file):
    header = [
        'Stepsheet Link',
        'Dance Name',
        'Song Name',
        'Trash',
        'Choreographers',
        'Level',
        'Counts'
    ]
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        for item in data:
            row = [item['url']] + item['row'] + [''] * (len(header) - 1 - len(item['row']))
            writer.writerow(row)

def main():
    last_line = get_last_line(INPUT_FILE)
    data = extract_links_and_context(last_line)
    write_to_csv(data, OUTPUT_FILE)
    print(f"Extracted {len(data)} CopperKnob links to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()

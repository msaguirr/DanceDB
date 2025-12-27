import re
import csv
from bs4 import BeautifulSoup

INPUT_FILE = 'assets/dance_sheet.html'
OUTPUT_FILE = 'assets/copperknob_links_extracted.csv'
MISSING_STEPSHEET_FILE = 'assets/dances_missing_stepsheet.csv'

def get_last_line(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        return lines[-1] if lines else ''

def clean_link(link):
    # Remove Google redirect prefix if present
    match = re.search(r'q=(https?://[^&]+)', link)
    if 'google.com/url?' in link and match:
        return match.group(1)
    return link

def extract_rows(html_line):
    soup = BeautifulSoup(html_line, 'html.parser')
    rows = []
    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        row_data = [td.get_text(strip=True) for td in tds]
        links = [clean_link(a['href']) for a in tr.find_all('a', href=True)]
        rows.append({'row': row_data, 'links': links})
    return rows

def write_to_csv(data, output_file, header):
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        for item in data:
            row = item['row']
            writer.writerow(row)

def main():
    last_line = get_last_line(INPUT_FILE)
    rows = extract_rows(last_line)
    header = [
        'Stepsheet Link',
        'Dance Name',
        'Song Name',
        'Trash',
        'Choreographers',
        'Level',
        'Counts'
    ]
    missing_header = [
        'Dance Name',
        'Song Name',
        'Trash',
        'Choreographers',
        'Level',
        'Counts',
        'Video Link'
    ]
    dances_with_stepsheet = []
    dances_missing_stepsheet = []
    # Skip the first two rows (header and possible subheader)
    data_rows = rows[2:]
    for row in data_rows:
        # Defensive: ensure enough columns
        if len(row['row']) < 3:
            continue
        dance_name = row['row'][0]
        song_name = row['row'][1]
        stepsheet_link = None
        video_link = None
        # Only look for stepsheet link in the third column (if present)
        if len(row['links']) > 0:
            for link in row['links']:
                if 'copperknob.co.uk/stepsheets/' in link:
                    stepsheet_link = link
                elif 'youtube.com' in link or 'youtu.be' in link or 'vimeo.com' in link:
                    video_link = link
        if stepsheet_link:
            dances_with_stepsheet.append({
                'row': [stepsheet_link, dance_name, song_name] + row['row'][3:]
            })
        else:
            base_row = [dance_name, song_name] + row['row'][3:]
            base_row = base_row + [''] * (len(missing_header) - 1 - len(base_row))
            base_row.append(video_link if video_link else '')
            dances_missing_stepsheet.append({'row': base_row})
    write_to_csv(dances_with_stepsheet, OUTPUT_FILE, header)
    write_to_csv(dances_missing_stepsheet, MISSING_STEPSHEET_FILE, missing_header)
    print(f"Extracted {len(dances_with_stepsheet)} dances with stepsheet links to {OUTPUT_FILE}")
    print(f"Extracted {len(dances_missing_stepsheet)} dances missing stepsheet links to {MISSING_STEPSHEET_FILE}")

    # After parsing, generate copperknob_links_and_songs.csv directly from parsed HTML data
    output_csv = 'assets/copperknob_links_and_songs.csv'
    with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(['Stepsheet Link', 'Dance Name', 'Song Name'])
        for item in dances_with_stepsheet:
            row = item['row']
            # Only write if all three fields are present
            if len(row) >= 3:
                writer.writerow([row[0], row[1], row[2]])
    print(f"Extracted Stepsheet Link, Dance Name, and Song Name to {output_csv}")

if __name__ == '__main__':
    main()

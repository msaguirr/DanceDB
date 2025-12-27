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
    # Extract just Stepsheet Link and Song Name from copperknob_links_extracted.csv
    input_csv = OUTPUT_FILE
    output_csv = 'assets/copperknob_links_and_songs.csv'
    with open(input_csv, 'r', encoding='utf-8') as infile, open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        # Write header
        writer.writerow(['Stepsheet Link', 'Song Name'])
        for i, row in enumerate(reader):
            if i == 0:
                continue  # skip header
            if len(row) >= 2:
                writer.writerow([row[0], row[1]])
    print(f"Extracted Stepsheet Link and Song Name to {output_csv}")
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
        # Find stepsheet link
        stepsheet_link = None
        video_link = None
        for link in row['links']:
            if 'copperknob.co.uk/stepsheets/' in link:
                stepsheet_link = link
            elif 'youtube.com' in link or 'youtu.be' in link or 'vimeo.com' in link:
                video_link = link
        if stepsheet_link:
            # Write to main output
            dances_with_stepsheet.append({
                'row': [stepsheet_link] + row['row'][1:]
            })
        else:
            # Write to missing stepsheet output
            # If row has enough columns, skip first (link) column
            base_row = row['row'][1:] if len(row['row']) == len(header) else row['row']
            # Pad to match missing_header length minus video link
            base_row = base_row + [''] * (len(missing_header) - 1 - len(base_row))
            base_row.append(video_link if video_link else '')
            dances_missing_stepsheet.append({'row': base_row})
    write_to_csv(dances_with_stepsheet, OUTPUT_FILE, header)
    write_to_csv(dances_missing_stepsheet, MISSING_STEPSHEET_FILE, missing_header)
    print(f"Extracted {len(dances_with_stepsheet)} dances with stepsheet links to {OUTPUT_FILE}")
    print(f"Extracted {len(dances_missing_stepsheet)} dances missing stepsheet links to {MISSING_STEPSHEET_FILE}")

if __name__ == '__main__':
    main()

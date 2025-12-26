import pandas as pd
import requests
from io import StringIO
from bs4 import BeautifulSoup

def fetch_google_sheet_csv(sheet_id: str, gid: str = '0'):
    """
    Fetch a Google Sheet as a pandas DataFrame using the public CSV export link.
    Args:
        sheet_id: The Google Sheet ID from the URL.
        gid: The sheet/tab GID (default '0' for first tab).
    Returns:
        pd.DataFrame
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}&range=A1:Z"
    resp = requests.get(url)
    resp.raise_for_status()
    # Google Sheets CSV export will only give us the display text, not the hyperlink. To get hyperlinks, fetch as HTML and parse.
    return pd.read_csv(StringIO(resp.text))

def fetch_google_sheet_html(sheet_id: str, gid: str = '0'):
    """
    Fetch a Google Sheet as HTML and extract hyperlinks from columns.
    Returns a list of dicts (rows), with hyperlinks for 'Step Sheet' and 'Videos' columns if present.
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/htmlview?gid={gid}"
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.find('table')
    rows = []
    headers = []
    for i, tr in enumerate(table.find_all('tr')):
        cells = tr.find_all(['th', 'td'])
        if i == 0:
            headers = [cell.get_text(strip=True) for cell in cells]
            continue
        row = {}
        for j, cell in enumerate(cells):
            col = headers[j] if j < len(headers) else f'col{j}'
            # If cell contains a hyperlink, extract the href
            a = cell.find('a')
            if a and a.has_attr('href'):
                row[col] = a['href']
            else:
                row[col] = cell.get_text(strip=True)
        rows.append(row)
    return rows

if __name__ == "__main__":
    SHEET_ID = "1hpTqg5uaUiYo80UmGNplzWqj1uZmLkUOWrEkl0YNMaQ"
    GID = "0"
    # Get hyperlinks from HTML
    rows = fetch_google_sheet_html(SHEET_ID, GID)
    # Show first 5 rows with Step Sheet and Videos hyperlinks
    for row in rows[:5]:
        print({k: row[k] for k in row if k in ('Dance', 'Step Sheet', 'Videos', 'Counts')})

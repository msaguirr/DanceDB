import requests
from bs4 import BeautifulSoup

def scrape_dance_info(url):
	"""
	Scrape dance info from a stepsheet web page.
	This is a sample for CopperKnob (adjust selectors for other sites).
	Returns a dict with keys: name, choreographer, level, notes
	"""
	try:
		resp = requests.get(url, timeout=10)
		resp.raise_for_status()
		soup = BeautifulSoup(resp.text, 'html.parser')

		# Example selectors for CopperKnob (adjust as needed)
		name = soup.find('h1').get_text(strip=True) if soup.find('h1') else ''
		choreo = ''
		level = ''
		notes = ''
		# Try to find choreographer and level in the info table
		info_table = soup.find('table', class_='table')
		if info_table:
			for row in info_table.find_all('tr'):
				th = row.find('th')
				td = row.find('td')
				if th and td:
					label = th.get_text(strip=True).lower()
					value = td.get_text(strip=True)
					if 'choreographer' in label:
						choreo = value
					elif 'level' in label:
						level = value
		# Notes or description (optional)
		desc = soup.find('div', class_='description')
		if desc:
			notes = desc.get_text(strip=True)
		return {
			'name': name,
			'choreographer': choreo,
			'level': level,
			'notes': notes
		}
	except Exception as e:
		print(f"Error scraping {url}: {e}")
		return None

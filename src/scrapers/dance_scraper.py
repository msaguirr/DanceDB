import requests
from bs4 import BeautifulSoup

def scrape_dance_info(url):
	"""
	Scrape dance info from a stepsheet web page.
	This is a sample for CopperKnob (adjust selectors for other sites).
	Returns a dict with keys: name, choreographer, level, notes
	"""
	try:
		headers = {
			'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
		}
		resp = requests.get(url, headers=headers, timeout=10)
		resp.raise_for_status()
		soup = BeautifulSoup(resp.text, 'html.parser')

		# Dance name from meta or title
		name = ''
		meta_title = soup.find('meta', attrs={'name': 'title'})
		if meta_title and meta_title.get('content'):
			name = meta_title['content']
		else:
			title_tag = soup.find('title')
			if title_tag:
				# e.g. "CopperKnob - Power Jam - Kathi Stringer"
				parts = title_tag.get_text(strip=True).split(' - ')
				if len(parts) >= 2:
					name = parts[1]

		# Choreographer from meta or title
		choreo = ''
		meta_desc = soup.find('meta', attrs={'name': 'description'})
		if meta_desc and meta_desc.get('content'):
			desc = meta_desc['content']
			# e.g. "22 Count 4 Wall Beginner Line Dance - Kathi Stringer"
			if '-' in desc:
				choreo = desc.split('-')[-1].strip()
		if not choreo:
			if title_tag and len(parts) >= 3:
				choreo = parts[2]

		# Level, count, wall from meta description
		level = ''
		count = ''
		wall = ''
		if meta_desc and meta_desc.get('content'):
			desc = meta_desc['content']
			# Try to extract e.g. "22 Count 4 Wall Beginner"
			import re
			m = re.match(r"(\d+) Count (\d+) Wall ([^-]+)", desc)
			if m:
				count = m.group(1)
				wall = m.group(2)
				level = m.group(3).strip()
			else:
				# fallback: just use the whole string before the dash
				level = desc.split('-')[0].strip()
			# Always strip 'Line Dance' from level if present
			if level.endswith('Line Dance'):
				level = level[:-len('Line Dance')].strip()

		# Notes: use meta description for now
		notes = meta_desc['content'] if meta_desc and meta_desc.get('content') else ''

		return {
			'name': name,
			'choreographer': choreo,
			'level': level,
			'count': count,
			'wall': wall,
			'notes': notes
		}
	except Exception as e:
		print(f"Error scraping {url}: {e}")
		return None

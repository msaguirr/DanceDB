import requests
import cloudscraper
from bs4 import BeautifulSoup

def parse_copperknob_html(filepath):
	"""
	Parse a CopperKnob HTML file and extract:
	title, choreographer, count, wall, level, music (title/artist), step sheet instructions.
	Returns a dict with these fields.
	"""
	with open(filepath, encoding='utf-8') as f:
		html = f.read()
	soup = BeautifulSoup(html, 'html.parser')


	# Dance Name (from h2.sectionbar or meta title)
	dance_name = ''
	h2_sectionbar = soup.find('h2', attrs={'style': True})
	if h2_sectionbar:
		dance_name = h2_sectionbar.get_text(strip=True)
	if not dance_name:
		meta_title = soup.find('meta', attrs={'name': 'title'})
		if meta_title and meta_title.get('content'):
			dance_name = meta_title['content']

	# Title (fallback to dance_name)
	title = dance_name

	# Choreographer(s) with name and country, and release date
	choreographers = []
	release_date = ''
	choreo_tag = soup.find('div', class_='sheetinfochoregrapher')
	if choreo_tag:
		choreo_spans = choreo_tag.find_all('span')
		print(choreo_spans)
		for span in choreo_spans:
			for part in span.stripped_strings:
				# Remove release date if present (e.g., ' - October 2019')
				part_clean = part
				if ' - ' in part:
					part_clean, possible_date = part.rsplit(' - ', 1)
					# Accept only if possible_date looks like a date (e.g., contains a month and year)
					if any(month in possible_date for month in [
						'January','February','March','April','May','June','July','August','September','October','November','December']):
						release_date = possible_date.strip()
				# Split on '&', 'and', and ','
				import re
				choreo_entries = re.split(r'\s*(?:&|and|,)\s*', part_clean)
				for entry in choreo_entries:
					entry = entry.strip()
					if not entry:
						continue
					# If entry is just a country (e.g., (Australia)), assign to previous choreographer
					if entry.startswith('(') and entry.endswith(')'):
						country_part = entry[1:-1].strip()
						if choreographers and not choreographers[-1]['country']:
							choreographers[-1]['country'] = country_part
						# else: ignore orphan country
					# If entry is Name (Country)
					elif '(' in entry and entry.endswith(')'):
						name_part = entry[:entry.rfind('(')].strip()
						country_part = entry[entry.rfind('(')+1:-1].strip()
						if name_part:
							choreographers.append({'name': name_part, 'country': country_part})
					# If entry is just a name
					else:
						choreographers.append({'name': entry, 'country': ''})

	# Count
	count = ''
	count_tag = soup.find('div', class_='sheetinfocount')
	if count_tag:
		count_span = count_tag.find('span')
		if count_span:
			count = count_span.get_text(strip=True)

	# Wall
	wall = ''
	wall_tag = soup.find('div', class_='sheetinfowall')
	if wall_tag:
		wall_span = wall_tag.find('span')
		if wall_span:
			wall = wall_span.get_text(strip=True)

	# Level
	level = ''
	level_tag = soup.find('div', class_='sheetinfolevel')
	if level_tag:
		level_div = level_tag.find('div', class_='leveltag')
		if level_div:
			level = level_div.get_text(strip=True)

	# Music
	song_title = ''
	song_artist = ''
	music_tag = soup.find('div', class_='sheetinfomusic')
	if music_tag:
		music_span = music_tag.find('span')
		if music_span:
			# Format: <A>Song Title</A> - Artist<br>
			a_tag = music_span.find('a')
			if a_tag:
				song_title = a_tag.get_text(strip=True)
				# The rest after the <a> is the artist
				text = music_span.get_text(separator=' ', strip=True)
				if ' - ' in text:
					song_artist = text.split(' - ', 1)[-1].split()[0]
					# Try to get full artist name
					after_dash = text.split(' - ', 1)[-1]
					song_artist = after_dash.split(' ', 1)[-1] if ' ' in after_dash else after_dash

	# Step Sheet Instructions
	steps = []
	sheetcontent = soup.find('div', class_='sheetcontent')
	if sheetcontent:
		current_section = ''
		for elem in sheetcontent.children:
			if elem.name == 'span' and 'title' in elem.get('class', []):
				current_section = elem.get_text(strip=True)
			elif elem.name == 'span' and 'step' in elem.get('class', []):
				step_num = elem.get_text(strip=True)
				# Next sibling is desc
				desc = ''
				next_elem = elem.find_next_sibling('span', class_='desc')
				if next_elem:
					desc = next_elem.get_text(strip=True)
				steps.append({'section': current_section, 'step': step_num, 'desc': desc})

	return {
		'dance_name': dance_name,
		'title': title,
		'choreographers': choreographers,  # list of dicts with name and country
		'release_date': release_date,
		'count': count,
		'wall': wall,
		'level': level,
		'song_title': song_title,
		'song_artist': song_artist,
		'steps': steps
	}

def scrape_dance_info(url):
	"""
	Scrape dance info from a stepsheet web page.
	This is a sample for CopperKnob (adjust selectors for other sites).
	Returns a dict with keys: name, choreographer, level, notes
	"""
	try:
		# Use cloudscraper to bypass Cloudflare protection
		scraper = cloudscraper.create_scraper()
		resp = scraper.get(url, timeout=15)
		resp.raise_for_status()
		# Save to a temporary file and parse with the same logic as parse_copperknob_html
		import tempfile
		with tempfile.NamedTemporaryFile('w+', encoding='utf-8', delete=False, suffix='.html') as tmp:
			tmp.write(resp.text)
			tmp.flush()
			result = parse_copperknob_html(tmp.name)
		return result
	except Exception as e:
		print(f"Error scraping {url}: {e}")
		return None

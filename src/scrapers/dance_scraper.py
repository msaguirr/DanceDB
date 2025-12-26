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
		for span in choreo_spans:
			for part in span.stripped_strings:
				import re
				choreo_entries = re.split(r'\s*(?:&|and|,)\s*', part)
				# If the last entry looks like a release date, extract it
				if choreo_entries:
					last_entry = choreo_entries[-1].strip()
					months = [
						'January','February','March','April','May','June','July','August','September','October','November','December']
					if any(month in last_entry for month in months):
						# Remove any leading dash or whitespace
						release_date = last_entry.lstrip('-').strip()
						choreo_entries = choreo_entries[:-1]
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

	# Music (extract all songs and switches)
	songs = []
	music_tag = soup.find('div', class_='sheetinfomusic')
	if music_tag:
		# Find all <span> and <a> tags that represent songs
		# The main song is usually in the first <span> with an <a>
		# Song switches may be in subsequent <span> or <br> separated lines
		music_spans = music_tag.find_all('span')
		for span in music_spans:
			# Each span may contain one or more songs (separated by <br> or multiple <a> tags)
			# Find all <a> tags in this span
			a_tags = span.find_all('a')
			for a_tag in a_tags:
				title = a_tag.get_text(strip=True)
				# Try to get artist: look for text after <a> and ' - '
				next_sibling = a_tag.next_sibling
				artist = ''
				if next_sibling:
					# Sometimes artist is after ' - '
					text = str(next_sibling)
					if ' - ' in text:
						artist = text.split(' - ', 1)[-1].strip()
					else:
						# Sometimes artist is just after the <a>
						artist = text.strip()
				# If artist is still empty, try to get from span text
				if not artist:
					span_text = span.get_text(separator=' ', strip=True)
					if ' - ' in span_text:
						artist = span_text.split(' - ', 1)[-1].strip()
				songs.append({'title': title, 'artist': artist})
		# If no <span>, fallback to direct <a> in music_tag
		if not songs:
			a_tags = music_tag.find_all('a')
			for a_tag in a_tags:
				title = a_tag.get_text(strip=True)
				next_sibling = a_tag.next_sibling
				artist = ''
				if next_sibling:
					text = str(next_sibling)
					if ' - ' in text:
						artist = text.split(' - ', 1)[-1].strip()
					else:
						artist = text.strip()
				songs.append({'title': title, 'artist': artist})
	# Backward compatibility: also set song_title and song_artist for main song
	song_title = songs[0]['title'] if songs else ''
	song_artist = songs[0]['artist'] if songs else ''

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
		'songs': songs,  # list of dicts with title/artist
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

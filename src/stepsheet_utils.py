import re

def extract_copperknob_id(url):
    """
    Extract the unique dance ID from a CopperKnob stepsheet URL.
    Example: https://www.copperknob.co.uk/stepsheets/34792/power-jam -> '34792'
    """
    match = re.search(r"/stepsheets/(\d+)/", url)
    if match:
        return match.group(1)
    return None

if __name__ == "__main__":
    # Example usage
    urls = [
        "https://www.copperknob.co.uk/stepsheets/34792/power-jam",
        "https://www.copperknob.co.uk/stepsheets/12345/another-dance",
        "https://www.copperknob.co.uk/stepsheets/99999/some-dance-title"
    ]
    ids = [extract_copperknob_id(url) for url in urls]
    print(ids)  # ['34792', '12345', '99999']

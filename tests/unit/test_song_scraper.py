#!/usr/bin/env python3
"""Test script to verify song page scraping from Copperknob."""

from copperknob_import_gui import CopperknobImporter

def test_song_extraction():
    """Test extracting song data from a Copperknob song page."""
    importer = CopperknobImporter()
    
    # Example song URLs from Copperknob
    # (Replace with actual URLs if these don't work)
    test_urls = [
        "https://www.copperknob.co.uk/song/boot-scootin-boogie-id1234",
        # Add more test URLs here
    ]
    
    print("Testing Song Data Extraction from Copperknob")
    print("=" * 60)
    
    # For testing, let's try extracting from a dance page first
    # and see if it finds the song link
    dance_url = "https://www.copperknob.co.uk/stepsheets/boot-scootin-boogie-ID12345"
    
    print(f"\n1. Testing dance page extraction (to find song link):")
    print(f"   URL: {dance_url}")
    print(f"   Note: Replace with actual Copperknob URL to test")
    
    # Uncomment below to test with real URL
    # data = importer.extract_dance_data(dance_url)
    # if data:
    #     print(f"\n   Results:")
    #     print(f"   - Dance: {data.get('dance_name')}")
    #     print(f"   - Song: {data.get('song_name')} by {data.get('artist')}")
    #     print(f"   - BPM: {data.get('bpm')}")
    #     print(f"   - Spotify: {data.get('spotify_url')}")
    #     print(f"   - Song URL: {data.get('song_url')}")
    # else:
    #     print("   Failed to extract data")
    
    print("\n" + "=" * 60)
    print("To test with a real URL:")
    print("1. Go to https://www.copperknob.co.uk")
    print("2. Find a step sheet")
    print("3. Copy the URL")
    print("4. Run the GUI and paste it in the URL field")
    print("5. Click 'Fetch Data from URL'")
    print("\nExpected behavior:")
    print("- Dance info should populate")
    print("- Song link should be followed automatically")
    print("- Song name, artist, BPM should be extracted")
    print("- Spotify URL should be found if available on the song page")

if __name__ == '__main__':
    test_song_extraction()

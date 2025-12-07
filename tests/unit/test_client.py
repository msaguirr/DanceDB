import unittest

from myspotipy.client import Spotify


class TestClient(unittest.TestCase):
    def test_auth_header(self):
        s = Spotify(access_token='abc123')
        self.assertIn('Authorization', s._session.headers)
        self.assertEqual(s._session.headers['Authorization'], 'Bearer abc123')

    def test_search_tracks_parsing(self):
        # Create a mock session that returns a predictable JSON payload
        class MockResponse:
            def __init__(self, data):
                self._data = data
                self.ok = True

            def json(self):
                return self._data

        class MockSession:
            def __init__(self, resp):
                self.headers = {}
                self._resp = resp

            def request(self, method, url, params=None, json=None, timeout=None):
                return self._resp

        sample = {
            "tracks": {
                "items": [
                    {
                        "id": "1",
                        "name": "Test Song",
                        "artists": [{"name": "Artist A"}],
                        "album": {"name": "Album X"},
                        "popularity": 50,
                        "uri": "spotify:track:1",
                        "preview_url": None,
                        "external_urls": {"spotify": "https://open.spotify.com/track/1"},
                    }
                ]
            }
        }

        mock_resp = MockResponse(sample)
        mock_sess = MockSession(mock_resp)

        s = Spotify(access_token='abc123', session=mock_sess)
        results = s.search_tracks('Test Song', artist='Artist A', k=1)
        self.assertEqual(len(results), 1)
        track = results[0]
        self.assertEqual(track['id'], '1')
        self.assertEqual(track['name'], 'Test Song')
        self.assertEqual(track['artists'], ['Artist A'])



if __name__ == '__main__':
    unittest.main()

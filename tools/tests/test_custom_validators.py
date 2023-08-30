from tools.custom_validators import *

class TestUrl:
    valid_url = [
    "http://www.google.co.uk",
    "https://www.google.co.uk",
    "http://google.co.uk",
    "https://google.co.uk",
    "http://www.google.co.uk/~as_db3.2123/134-1a",
    "https://www.google.co.uk/~as_db3.2123/134-1a",
    "http://google.co.uk/~as_db3.2123/134-1a",
    "https://google.co.uk/~as_db3.2123/134-1a",
    "https://localhost:5000/",
    "https://google-like.com",
    "https://username:password@example.com",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    ]

    invalid_url = [
    "www.google.co.uk",
    "google.co.uk",
    "www.google.co.uk/~as_db3.2123/134-1a",
    "google.co.uk/~as_db3.2123/134-1a",
    "https://https://www.google.co.uk",
    "https://...",
    "https://..",
    "https://.",
    "https://.google.com",
    "https://..google.com",
    "https://...google.com",
    "https://.google..com",
    "https://.google...com"
    "https://...google..com",
    "https://...google...com",
    ".google.com",
    ".google.co.",
    ]

    validator = Url()
    def test_valid_urls(self):
        for url in self.valid_url:
            assert self.validator._is_valid(url)


    def test_invalid_urls(self):
        for url in self.invalid_url:
            assert not self.validator._is_valid(url)

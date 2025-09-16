# import trafilatura
#
#
# class TrafilaturaScraper:
#     def __init__(self, url: str):
#         self.url = url
#         self.downloaded_content = None
#         self.extracted_text = None
#
#     def fetch_content(self) -> bool:
#         self.downloaded_content = trafilatura.fetch_url(self.url)
#         return self.downloaded_content is not None
#
#     def extract_content(self) -> bool:
#         if not self.downloaded_content:
#             return False
#         self.extracted_text = trafilatura.extract(self.downloaded_content)
#         return self.extracted_text is not None
#
#     def get_clean_text(self) -> str:
#         if not self.fetch_content():
#             return "No content could be fetched from the provided URL."
#         if not self.extract_content():
#             return "No content could be extracted from the provided URL."
#         return self.extracted_text.strip()

import requests
from bs4 import BeautifulSoup


class TrafilaturaScraper:
    def __init__(self, url, headers=None):
        self.url = url
        self.headers = headers or {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        self.raw_html = None
        self.soup = None

    def fetch_content(self):
        """
        Makes an HTTP GET request to fetch raw HTML.
        Stores the HTML in self.raw_html.
        """
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()  # Raises HTTPError for bad codes
            self.raw_html = response.content
            print(f"[INFO] Fetched content from {self.url}")
        except requests.RequestException as e:
            print(f"[ERROR] Failed to fetch content: {e}")
            self.raw_html = None

    def parse_content(self):
        """
        Parses the HTML into BeautifulSoup object and removes
        script/style tags for cleaner text extraction.
        """
        if self.raw_html is None:
            print("[ERROR] No raw HTML to parse. Did you call fetch_content()?")
            return

        self.soup = BeautifulSoup(self.raw_html, "html.parser")

        # Remove script and style tags
        for tag in self.soup(["script", "style"]):
            tag.decompose()

        print("[INFO] Parsed HTML and removed script/style tags.")

    def get_clean_text(self, separator="\n", strip=True):
        """
        Extracts clean text from soup object, removing empty lines.
        Returns a list of text lines.
        """
        if self.soup is None:
            print("[ERROR] Soup object is None. Did you call parse_content()?")
            return []

        text = self.soup.get_text(separator=separator, strip=strip)

        # Split into lines and remove empty ones
        lines = [line for line in text.split(separator) if line.strip()]
        return separator.join(lines)

from phi.tools import Toolkit
from app.utils.trafilatura_scraper import TrafilaturaScraper


class TrafilaturaTools(Toolkit):
    def __init__(self):
        super().__init__(name="trafilatura_tools")
        self.register(self.scrape_website)

    def scrape_website(self, url: str) -> str:
        """Scrape a webpage using Trafilatura to extract clean text."""
        try:
            print(f"🟢 TrafilaturaTool running for URL: {url}")
            scraper = TrafilaturaScraper(url)
            scraper.fetch_content()
            scraper.parse_content()
            return scraper.get_clean_text()
        except Exception as e:
            print(f"🔴 Error in TrafilaturaTool for URL {url}: {str(e)}")
            return f"Error scraping {url}: {str(e)}"

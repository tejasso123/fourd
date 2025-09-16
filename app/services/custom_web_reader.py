from phi.document.reader.website import WebsiteReader
from phi.document import Document
from typing import List


class CustomWebsiteReader(WebsiteReader):
    def read(self, url: str) -> List[Document]:
        # Ensure fresh crawl every time
        self._urls_to_crawl = [(url, 0)]
        self._visited = set()
        return super().read(url)

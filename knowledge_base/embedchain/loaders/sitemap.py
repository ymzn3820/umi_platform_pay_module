import concurrent.futures
import hashlib
import logging
from urllib.parse import urlparse

import requests
from tqdm import tqdm

try:
    from bs4 import BeautifulSoup
    from bs4.builder import ParserRejectedMarkup
except ImportError:
    raise ImportError(
        'Sitemap requires extra dependencies. Install with `pip install --upgrade "embedchain[dataloaders]"`'
    ) from None

from knowledge_base.embedchain.helpers.json_serializable import register_deserializable
from knowledge_base.embedchain.loaders.base_loader import BaseLoader
from knowledge_base.embedchain.loaders.web_page import WebPageLoader


@register_deserializable
class SitemapLoader(BaseLoader):
    """
    This method takes a sitemap URL as input and retrieves
    all the URLs to use the WebPageLoader to load content
    of each page.
    """

    def load_data(self, sitemap_url):
        output = []
        web_page_loader = WebPageLoader()

        if urlparse(sitemap_url).scheme not in ["file", "http", "https"]:
            raise ValueError("Not a valid URL.")

        if urlparse(sitemap_url).scheme in ["http", "https"]:
            response = requests.get(sitemap_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "xml")
        else:
            with open(sitemap_url, "r") as file:
                soup = BeautifulSoup(file, "xml")

        links = [link.text for link in soup.find_all("loc") if link.parent.name == "url"]
        if len(links) == 0:
            links = [link.text for link in soup.find_all("loc")]

        doc_id = hashlib.sha256((" ".join(links) + sitemap_url).encode()).hexdigest()

        def load_web_page(link):
            try:
                loader_data = web_page_loader.load_data(link)
                return loader_data.get("data")
            except ParserRejectedMarkup as e:
                logging.error(f"Failed to parse {link}: {e}")
            return None

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_link = {executor.submit(load_web_page, link): link for link in links}
            for future in tqdm(concurrent.futures.as_completed(future_to_link), total=len(links), desc="Loading pages"):
                link = future_to_link[future]
                try:
                    data = future.result()
                    if data:
                        output.extend(data)
                except Exception as e:
                    logging.error(f"Error loading page {link}: {e}")

        return {"file_id": doc_id, "data": output}

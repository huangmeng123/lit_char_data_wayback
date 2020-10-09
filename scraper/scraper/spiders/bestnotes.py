# -*- coding: utf-8 -*-
"""
This Scrapy module provides parsers for thebestnotes.com website. To create the parsers
use devtools to inspect webpage and find unique CSS classes or elements. Then check with
scrapy shell to discover appropriate CSS/xpath selectors, for example:

    $> scrapy shell 'http://thebestnotes.com/list/titlesB.html'
    >>> href = response.css('div.large-7 > p > a::attr(href)')[0].get()
    >>> href
    '/booknotes/Bean_Trees/Bean_Trees01.html'
    >>> follow = response.urljoin(href)
    >>> follow
    'http://thebestnotes.com/booknotes/Bean_Trees/Bean_Trees01.html'
    >>> fetch(follow)
    2020-02-20 03:59:52 [scrapy.core.engine] DEBUG: Crawled (200) ...<SNIP>...

"""
import string, logging
from scrapy import Request, Spider

from scraper.items import LiteratureInfo, CharacterInfo

SPIDER_NAME = 'bestnotes'

logging.basicConfig(
    filename='runtime.log', 
    format='%(asctime)s %(message)s', 
    filemode='w',
)

logger = logging.getLogger(f'{SPIDER_NAME}-logger')
logger.setLevel(logging.DEBUG)

UPPERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
LOWERS = 'abcdefghijklmnopqrstuvwxyz'

class BestnotesSpider(Spider):
    """
    Scrapy spider for extracting notes from thebestnotes.com website.
    """

    name = SPIDER_NAME
    allowed_domains = ["thebestnotes.com"]
    custom_settings = {
        'DOWNLOAD_DELAY': 0.1,
        # 'ITEM_PIPELINES': {
        #    'scrapynotes.pipelines.ScrapynotesProdPipeline': 300,
        # },
    }

    def start_requests(self):
        """Yield `Request(url)`s to be scraped. The list of urls is created by observing the actual website."""

        indices = set(string.ascii_uppercase) - set("QRUXYZ")  # cSpell:disable-line
        indices.add("NUM")
        prefix = "http://thebestnotes.com/list/titles"
        urls = [f"{prefix}{id}.html" for id in indices]

        for url in urls:
            yield Request(url=url, callback=self.parse_index)

    def parse_index(self, response):
        """parse the index page of bestnotes and yield Request to book page"""

        for book in response.css("div.large-7 p a"):
            # Remove \r\n and other extraneous whitespace
            book_title = " ".join(book.css("::text").get().split())
            href = book.css("::attr(href)").get()

            book_url = response.urljoin(href)

            yield Request(
                book_url,
                callback=self.parse_book,
                meta={
                    'book_title': book_title,
                },
            )

    def parse_book(self, response):
        """Parse book page to yield summary url"""

        book_title = response.meta['book_title']

        xpath_constrains = "contains(., 'Summary') and "
        xpath_constrains += "contains(., 'Synopsis')"
        summary_block = response.xpath(f"//a[{xpath_constrains}]")
        if len(summary_block) == 1:
            # We found URL to character list
            summary_url = response.urljoin(summary_block.attrib["href"])
            # yield LiteratureInfo(
            #     book_title=book_title,
            #     source=SPIDER_NAME,
            #     book_url=response.url,
            #     summary_url=summary_url,
            # )
            yield Request(
                summary_url,
                callback=self.parse_summary,
                meta={
                    'book_title': book_title,
                },
            )
        else:
            self.logger.warning(
                f"Found {summary_block=}, but no unique link in {response.url}"
            )


        """Parse book page to yield character information url"""
        xpath_constrains = "contains(., 'Character') and ("
        xpath_constrains += "contains(., 'List') or "
        xpath_constrains += "contains(., 'Major') or "
        xpath_constrains += "contains(., 'Minor')"
        xpath_constrains += ")"
        character_list_block = response.xpath(f"//a[{xpath_constrains}]")
        if len(character_list_block) == 1:
            # We found URL to character list
            character_list_url = response.urljoin(character_list_block.attrib["href"])
            # yield LiteratureInfo(
            #     book_title=book_title,
            #     source=SPIDER_NAME,
            #     book_url=response.url,
            #     character_list_url=character_list_url,
            # )
            yield Request(
                character_list_url,
                callback=self.parse_characters,
                meta={
                    'book_title': book_title,
                },
            )
        else:
            self.logger.warning(
                f"Found {character_list_block=}, but no unique link in {response.url}"
            )

    def parse_summary(self, response):
        """Parse summary url to extract summary"""
        possible_blocks = ["h2", "h2/b", "h6"]
        xpath_constrains = "contains(translate(., 'INOPSY', 'inopsy'), 'synopsis')"
        selector = f"[{xpath_constrains}]/following-sibling::p"

        for block in possible_blocks:
            summary_blocks = response.xpath(f"//{block}{selector}")

            if summary_blocks:
                break  # we found character descriptions

        summary = []
        for block in summary_blocks:
            paragraph = " ".join(
                filter(None, (x.strip() for x in block.xpath("text()").getall()))
            )
            if not paragraph:
                self.logger.warning(
                    f"{paragraph=} not found in {response.url} for block {block=}"
                )
                continue

            # Remove extraneous space
            paragraph = " ".join(paragraph.split())
            summary.append(paragraph)

        summary_text = '/n'.join(summary)
        logger.info(f'{summary_text=}')

        # yield LiteratureInfo(
        #     source=SPIDER_NAME,
        #     summary_url=response.url,
        #     summary_text="/n".join(summary),
        # )


    def parse_characters(self, response):
        """Parse character list url to extract characters' name and description"""
        possible_blocks = ["h2", "h6", "strong"]
        selector = '[re:test(., "(Major|Minor).*Characters")]/following-sibling::p'

        for block in possible_blocks:
            char_blocks = response.xpath(f"//{block}{selector}")

            if char_blocks:
                break  # we found character descriptions

        for i, char in enumerate(char_blocks):
            # The character name is inside bold tag
            char_name = " ".join(
                filter(
                    None,
                    (x.strip() for x in char.xpath(".//b").xpath(".//text()").getall()),
                )
            )
            if not char_name:
                self.logger.warning(
                    f"{char_name=} not found in {response.url} for block {char=}"
                )
                continue

            # Remove extraneous space
            char_name = " ".join(char_name.split())

            # Character description is in the remaining text nodes
            char_description = " ".join(
                filter(None, (x.strip() for x in char.xpath("text()").getall()))
            )
            if not char_description:
                self.logger.warning(
                    f"{char_description=} not found in {response.url} for block {char=}"
                )
                continue

            # Remove extraneous space
            char_description = " ".join(char_description.split())

            # yield CharacterInfo(
            #     character_list_url=response.url,
            #     name=char_name,
            #     character_order=i,
            #     description_url=response.url,
            #     description_text=char_description,
            # )

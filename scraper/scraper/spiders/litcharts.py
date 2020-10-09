# -*- coding: utf-8 -*-
from scrapy import Spider, Request
import logging

from scraper.items import LiteratureInfo, CharacterInfo
from scraper.utils import remove_html_tags, clean_text_or_none

SPIDER_NAME = 'litcharts'

# Remove all handlers associated with the root logger object.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    filename='runtime.log', 
    format='%(asctime)s %(message)s', 
    filemode='w',
) 

logger = logging.getLogger(f'{SPIDER_NAME}-logger')
logger.setLevel(logging.DEBUG)

class LitChartsSpider(Spider):
    name = SPIDER_NAME
    allowed_domains = ['litcharts.com']
    start_urls = ['https://www.litcharts.com']
    custom_settings = {
        'DOWNLOAD_DELAY': 0.1,
        # 'ITEM_PIPELINES': {
        #    'scrapynotes.pipelines.LCDataScraperProdPipeline': 300,
        # },
    }

    def parse(self, response):
        index_selectors = response.xpath(
            '//a[@class="filter-entry" and @data-filter != "all"]',
        )
        for selector in index_selectors:
            href = selector.xpath('./@href').get()
            url = response.urljoin(href)
            yield Request(
                url=url,
                callback=self.parse_page,
            )
    
    def parse_page(self, response):
        book_selectors = response.xpath('//a[contains(@class, "guide-panel")]')
        for selector in book_selectors:
            book_title = selector.xpath('.//div[@class="title"]/text()').get()
            book_title = clean_text_or_none(book_title)
            if book_title is None: continue

            author = selector.xpath('.//div[@class="author"]/text()').get()
            author = clean_text_or_none(author)

            book_href = selector.xpath('./@href').get()
            book_url = response.urljoin(book_href)
            book = LiteratureInfo(
                book_title=book_title,
                source=SPIDER_NAME,
                author=author,
                book_url=book_url,
            )
            yield Request(
                url=book_url,
                callback=self.parse_book,
                cb_kwargs={
                    'book': book,
                },
                dont_filter=True,
            )

    def parse_book(self, response, book):
        # get summary url
        conditions = (
            '@class="naked title" and contains(text(), ": Plot Summary")'
        )
        summary_href = response.xpath(
            f'//a[descendant::h3[{conditions}]]/@href',
        ).get()
        summary_url = response.urljoin(summary_href)
        book['summary_url'] = summary_url
        yield Request(
            url=summary_url,
            callback=self.parse_summary,
            cb_kwargs={
                'book_title': book['book_title'],
            },
            dont_filter=True,
        )
        
        # get character list url
        conditions = (
            '@class="naked title" and contains(text(), ": Characters")'
        )
        character_list_href = response.xpath(
            f'//a[descendant::h3[{conditions}]]/@href',
        ).get()
        character_list_url = response.urljoin(character_list_href)
        book['character_list_url'] = character_list_url
        yield Request(
            url=character_list_url,
            callback=self.parse_character_list,
            cb_kwargs={
                'book_title': book['book_title'],
            },
            dont_filter=True,
        )

        yield book

    def parse_summary(self, response, book_title):
        paragraphs = response.xpath('//p[@class="plot-text"]').extract()
        if len(paragraphs) == 0:
            logger.error(f'No summary for {response.url}')
        else:
            summary_text = ' '.join(map(remove_html_tags, paragraphs))
            summary_text = clean_text_or_none(summary_text)
            yield LiteratureInfo(
                book_title=book_title,
                source=SPIDER_NAME,
                summary_url=response.url,
                summary_text=summary_text,
            )

    def parse_character_list(self, response, book_title):
        character_nodes = response.xpath(
            '//div[contains(@class, "character index-list-item")]',
        )

        # parse major characters
        for i, node in enumerate(character_nodes):
            character_name = node.xpath('.//h2/text()').get()
            character_name = clean_text_or_none(character_name)
            if character_name is None:
                logger.error(f'No character name for {response.url}')
                continue

            href = response.xpath(
                './/a[starts-with(text(), "read analysis of ")]/@href',
            ).get()
            url = response.urljoin(href)
            yield Request(
                url=url,
                callback=self.parse_major_character,
                cb_kwargs={
                    'book_title': book_title,
                    'character_name': character_name,
                    'character_order': i,
                },
                dont_filter=True,
            )

        # parse minor characters
        minor_character_nodes = response.xpath(
            '//div[@class="character readable"]',
        )
        for node in minor_character_nodes:
            name = node.xpath('.//div["name"]/text()').get()
            name = clean_text_or_none(name)
            if name is None:
                continue

            classes = 'no-inline-characters no-inline-symbols no-inline-terms'
            paragraphs = node.xpath(f'.//div[@class="{classes}"]').extract()
            if len(paragraphs) == 0:
                logger.error(
                    f'No description for minor character {name} - {response.url}',
                )
            else:
                description_text = ' '.join(map(remove_html_tags, paragraphs))
                description_text = clean_text_or_none(description_text)
                yield CharacterInfo(
                    character_name=name,
                    book_title=book_title,
                    source=SPIDER_NAME,
                    description_url=response.url,
                    description_text=description_text,
                    character_order=100,
                )
            

    def parse_major_character(
        self,
        response,
        book_title,
        character_name,
        character_order,
    ):
        paragraphs = response.xpath(
            '//div[@class="highlightable-content"]',
        ).extract()
        if len(paragraphs) == 0:
            logger.error(
                f'No description for {response.url}',
            )
        else:
            description_text = ' '.join(map(remove_html_tags, paragraphs))
            description_text = clean_text_or_none(description_text)
            yield CharacterInfo(
                character_name=character_name,
                book_title=book_title,
                source=SPIDER_NAME,
                description_url=response.url,
                description_text=description_text,
                character_order=character_order,
            )

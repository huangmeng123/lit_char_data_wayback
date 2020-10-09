# -*- coding: utf-8 -*-
from scrapy import Spider, Request
import logging

from scraper.items import LiteratureInfo, CharacterInfo
from scraper.utils import remove_html_tags, clean_text_or_none

SPIDER_NAME = 'gradesaver'

# Remove all handlers associated with the root logger object.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    filename='runtime-dev.log', 
    format='%(asctime)s %(message)s', 
    filemode='w',
) 

logger = logging.getLogger(f'{SPIDER_NAME}-logger')
logger.setLevel(logging.DEBUG)

class GradeSaverSpider(Spider):
    name = SPIDER_NAME
    allowed_domains = ['gradesaver.com']
    start_urls = ['https://www.gradesaver.com/study-guides']
    custom_settings = {
        'DOWNLOAD_DELAY': 0.1,
        'ITEM_PIPELINES': {
           'scraper.pipelines.LCDataScraperDevPipeline': 300,
        },
    }

    def parse(self, response):
        index_selectors = response.xpath(
            '//a[@class="alphabits__links"]',
        )
        for selector in index_selectors:
            href = selector.xpath('./@href').get()
            url = response.urljoin(href)
            yield Request(
                url=url,
                callback=self.parse_page,
            )
    
    def parse_page(self, response):
        book_nodes = response.xpath('//li[@class="columnList__item"]')
        for node in book_nodes:
            title = node.xpath(
                './/a[@class="columnList__link"]/span/text()',
            ).get()
            title = clean_text_or_none(title)
            if title is None:
                logger.error(f'Missing book title for {response.url}')
                continue

            author = node.xpath(
                './/span[@class="linkList__link--secondary"]/a/text()',
            ).get()
            author = clean_text_or_none(author)
            if author is None:
                logger.error(f'Missing author for {title} - {response.url}')
            
            href = node.xpath(
                './/a[@class="columnList__link"]/@href',
            ).get()
            url = response.urljoin(href)
            
            yield Request(
                url=url,
                callback=self.parse_book,
                cb_kwargs={
                    'book_title': title,
                    'author': author,
                },
                dont_filter=True,
            )

    def parse_book(self, response, book_title, author):
        summary_href = response.xpath(
            '//a[contains(@class, "navSection__link") '
            'and contains(text(), " Summary")]/@href',
        ).get()
        if summary_href is not None:
            summary_url = response.urljoin(summary_href)
            yield Request(
                url=summary_url,
                callback=self.parse_summary,
                cb_kwargs={
                    'book_title': book_title,
                },
                dont_filter=True,
            )
        else:
            logger.error(f'Missing summary url - {response.url}')
            summary_url = None

        character_list_href = response.xpath(
            '//a[contains(@class, "navSection__link") '
            'and text()="Character List"]/@href',
        ).get()
        if character_list_href is not None:
            character_list_url = response.urljoin(character_list_href)
            yield Request(
                url=character_list_url,
                callback=self.parse_character_list,
                cb_kwargs={
                    'book_title': book_title,
                },
                dont_filter=True,
            )
        else:
            logger.error(f'Missing character list url - {response.url}')
            character_list_url = None

        # yield LiteratureInfo(
        #     book_title=book_title,
        #     source=SPIDER_NAME,
        #     author=author,
        #     book_url=response.url,
        #     summary_url=summary_url,
        #     character_list_url=character_list_url,   
        # )

    def parse_summary(self, response, book_title):
        paragraphs = response.xpath(
            '//article[@class="section__article" and @role="article"]/p',
        ).extract()
        summary_text = ' '.join(map(remove_html_tags, paragraphs))
        summary_text = clean_text_or_none(summary_text)
        if summary_text is None:
            logger.error(f'Missing summary - {response.url}')
        yield LiteratureInfo(
            book_title=book_title,
            source=SPIDER_NAME,
            summary_url=response.url,
            summary_text=summary_text,
        )

    def parse_character_list(self, response, book_title):
        character_nodes = response.xpath('//section[@class="linkTarget"]')
        for i, node in enumerate(character_nodes):
            name = node.xpath('./h2/text()').get()
            name = clean_text_or_none(name)
            if name is None:
                logger.error(f'Missing character name with order {i} - {response.url}')
                continue

            paragraphs = node.xpath('./p').extract()
            description_text = ' '.join(map(remove_html_tags, paragraphs))
            description_text = clean_text_or_none(description_text)
            if description_text is None:
                logger.error(f'Missing description for {name} - {response.url}')
            
            yield CharacterInfo(
                character_name=name,
                book_title=book_title,
                source=SPIDER_NAME,
                character_list_url=response.url,
                character_order=i,
                description_url=response.url,
                description_text=description_text,
            )
            
# -*- coding: utf-8 -*-
from re import L
from scrapy import Spider, Request
import logging

from scraper.utils import remove_html_tags, clean_text_or_none

SPIDER_NAME = 'smashwords'

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

class SmashwordsSpider(Spider):
    name = SPIDER_NAME
    allowed_domains = ['smashwords.com']
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        # 'ITEM_PIPELINES': {
        #    'scraper.pipelines.LCDataScraperProdPipeline': 300,
        # },
    }

    def start_requests(self):
        base = 'https://www.smashwords.com/books/category/1/newest/0/free/any/'
        indices = range(0, 75961, 20)
        # indices = range(0, 21, 20)
        start_urls = [base+str(ind) for ind in indices]
        for url in start_urls:
            yield Request(url=url, callback=self.parse)

    def parse(self, response):
        book_chunks = response.css('div.library-book > div.text')
        
        for book_chunk in book_chunks:
            title = book_chunk.css('a.library-title::text').get()
            title = clean_text_or_none(title)
            if title is None:
                logger.error(f'Missing book title - {response.url}')
                continue

            author = book_chunk.css(
                'span.library-by-line > a > span::text').get()
            author = clean_text_or_none(author)
            
            yield {
                'title': title,
                'author': author,
            }

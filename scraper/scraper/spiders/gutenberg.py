# -*- coding: utf-8 -*-
from re import L
from scrapy import Spider, Request
import logging

from scraper.utils import remove_html_tags, clean_text_or_none

SPIDER_NAME = 'gutenberg'

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

class GutenbergSpider(Spider):
    name = SPIDER_NAME
    allowed_domains = ['gutenberg.org']
    custom_settings = {
        'DOWNLOAD_DELAY': 5,
        # 'ITEM_PIPELINES': {
        #    'scraper.pipelines.LCDataScraperProdPipeline': 300,
        # },
    }

    def start_requests(self):
        base = 'https://www.gutenberg.org/browse/titles/'
        indices = list('abcdefghijklmnopqrstuvwxyz') + ['other']
        # indices = ['a']
        start_urls = [base+ind for ind in indices]
        for url in start_urls:
            yield Request(url=url, callback=self.parse)

    def parse(self, response):
        book_chunks = response.css('div.pgdbbytitle > h2')
        author_chunks = response.css('div.pgdbbytitle > p')
        assert(len(book_chunks) == len(author_chunks))
        
        for book_chunk, author_chunk in zip(book_chunks, author_chunks):
            title_node = book_chunk.css('a').get()
            lines = title_node.strip().split('<br>')
            lines = list(map(remove_html_tags, lines))
            title = ' '.join(lines)
            title = ' '.join(title.split())

            url = book_chunk.xpath('./a/@href').get()

            lang = book_chunk.xpath('./text()').get()
            lang = lang.strip()
            assert(lang[0] == '(' and lang[-1] == ')')
            lang = lang[1:-1]

            is_audio_book = False
            if book_chunk.css('img.pgdbflag').get() is not None:
                is_audio_book = True

            author = author_chunk.xpath('./a/text()').get()
            author = clean_text_or_none(author)

            info = {
                'title': title,
                'language': lang,
                'author': author,
                'book_url': response.urljoin(url),
                'is_audio_book': is_audio_book,
            }
            
            # yield Request(
            #     url=info['book_url'],
            #     callback=self.parse_text_url,
            #     cb_kwargs={
            #         'book_info': info,
            #     },
            # )

            yield info

    def parse_text_url(self, response, book_info):
        book_content_url = response.xpath("//a[text()='Plain Text UTF-8']/@href").get()
        if book_content_url is not None:
            book_info['content_url'] = response.urljoin(book_content_url)
        yield book_info

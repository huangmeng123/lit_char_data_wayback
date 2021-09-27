# -*- coding: utf-8 -*-
from scrapy import Spider, Request, signals
import logging
import os, re

from scraper.items import LiteratureInfo
from scraper.utils import clean_text_or_none, remove_html_tags
from scrapy.utils.log import configure_logging

_ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
_STATIC_DIR = os.path.join(_ROOT_DIR, 'static')
_INPUT_DIR = os.path.join(_ROOT_DIR, 'input')
_OUTPUT_DIR = os.path.join(_ROOT_DIR, 'output')

ALL_URLS_FILENAME = os.path.join(_STATIC_DIR, 'list_literatures_cached.txt')

INPUT_URLS_FILENAME = os.path.join(_INPUT_DIR, 'list_literatures_retry.txt')
OUTPUT_URLS_FILENAME = os.path.join(_OUTPUT_DIR, 'list_literatures_failed.txt')

LOG_PATH = os.path.join(_OUTPUT_DIR, 'wayback_lit_runtime.log')


LOG_ENABLED = False
# Disable default Scrapy log settings.
configure_logging(install_root_handler=False)

logger = logging.getLogger('wayback-lit')
logger.setLevel(logging.INFO)
_ch = logging.FileHandler(LOG_PATH, 'w+')
_ch.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
logger.addHandler(_ch)

class WaybackLitSpider(Spider):
    name = 'wayback_lit'
    allowed_domains = ['web.archive.org']
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'ITEM_PIPELINES': {
           'scraper.pipelines.LCDataScraperDatabasePipeline': 300,
        },
    }

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(WaybackLitSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def start_requests(self):
        

        urls = []
        if INPUT_URLS_FILENAME is not None:
            with open(INPUT_URLS_FILENAME) as in_f:
                urls = [
                    line.strip() for line in in_f.readlines()
                    if len(line.strip()) > 0
                ]
        if len(urls) == 0:
            with open(ALL_URLS_FILENAME) as in_f:
                urls = [
                    line.strip() for line in in_f.readlines()
                    if len(line.strip()) > 0
                ]

        self.failed_urls = set()

        for url in urls:
            yield Request(url=url, callback=self.validate_response, cb_kwargs={'orig_url': url})

    def spider_closed(self, spider):
        self.crawler.stats.set_value('failed_urls', ', '.join(self.failed_urls))
        with open(OUTPUT_URLS_FILENAME, 'w') as out_f:
            for url in self.failed_urls:
                out_f.write(url+'\n')

    @staticmethod
    def get_base_url(url):
        pattern = r'^http:\/\/web.archive.org\/web\/(\d{14})\/http(?:s):\/\/(.*)$'
        result = re.search(pattern, url)
        if result is None: return None
        return (result.group(1), result.group(2))

    def validate_response(self, response, orig_url):
        orig_base_url = self.get_base_url(orig_url)
        response_base_url = self.get_base_url(response.url)
        if orig_base_url != response_base_url:
            logger.error(f'expect {orig_url}, but got {response.url}')
            self.failed_urls.add(orig_url)
            return

        url = response.url
        if 'www.sparknotes.com/' in url:
            for result in self.parse_sparknotes_lit(response):
                yield result
        elif 'www.cliffsnotes.com/' in url:
            for result in self.parse_cliffnotes_lit(response):
                yield result
        elif 'www.shmoop.com/' in url:
            for result in self.parse_shmoop_lit(response):
                yield result
        elif 'www.litcharts.com/' in url:
            for result in self.parse_litcharts_lit(response):
                yield result
        else:
            logger.error(f'Invalid url - {url}')
            self.failed_urls.add(response.url)


    def get_author_name(self, response, selector_paths):
        for path in selector_paths:
            author = response.css(path).get()
            if author is not None:
                return ' '.join(author.strip().split())
        return None

    def parse_sparknotes_lit(self, response):
        # get book title
        title = response.css('h1.TitleHeader_title::text').get()
        if title is None:
            logger.error(f'Missing book title - {response.url}')
            self.failed_urls.add(response.url)
            return
        title = ' '.join(title.strip().split())

        # get book author
        author = self.get_author_name(
            response=response,
            selector_paths=[
                'div.TitleHeader_authorName::text',
                'a.TitleHeader_authorLink::text',
            ],
        )
        if author is None:
            logger.error(f'Missing author name - {response.url}')
            self.failed_urls.add(response.url)

        # get summary
        paragraphs = response.xpath('//*[@id="plotoverview"]/p/text()').extract()
        summary_text = ' '.join(map(remove_html_tags, paragraphs))
        summary_text = clean_text_or_none(summary_text)
        if summary_text is None:
            logger.error(f'Missing summary - {response.url}')
            self.failed_urls.add(response.url)
            return

        yield LiteratureInfo(
            book_title=title,
            source='sparknotes',
            author=author,
            summary_url=response.url,
            summary_text=summary_text,
        )
    
    def parse_cliffnotes_lit(self, response):
        # get book title
        title = response.css('div.title-wrapper > h1::text').get()
        if title is None:
            logger.error(f'Missing book title - {response.url}')
            self.failed_urls.add(response.url)
            return
        title = ' '.join(title.strip().split())

        # get book author
        author = response.css('div.title-wrapper > h2::text').get()
        if author is None:
            logger.error(f'Missing author name - {response.url}')
            self.failed_urls.add(response.url)
        else:
            author = ' '.join(author.strip().split())

        # get book summary
        paragraphs = response.css('p.litNoteText').extract()
        summary_text = ' '.join(map(remove_html_tags, paragraphs))
        summary_text = clean_text_or_none(summary_text)
        if summary_text is None:
            logger.error(f'Missing summary - {response.url}')
            self.failed_urls.add(response.url)
            return
        
        yield LiteratureInfo(
            book_title=title,
            source='cliffnotes',
            author=author,
            summary_url=response.url,
            summary_text=summary_text,
        )

    def parse_shmoop_lit(self, response):
        # get book title
        title = response.css('ul.items > li:nth-child(4) > a::text').get()
        title = clean_text_or_none(title)
        if title is None:
            logger.error(f'Missing book title - {response.url}')
            self.failed_urls.add(response.url)
            return

        # get book author
        author = response.css('span.author-name::text').get()
        author = clean_text_or_none(author)
        if author is None:
            logger.error(f'Missing author name - {response.url}')
            self.failed_urls.add(response.url)
            return

        # get summary
        summary = response.xpath(
            '//div[@data-class="SHPlotOverviewSection"]/p',
        ).extract()
        if len(summary) == 0:
            summary = response.xpath(
                '//div[@class="content-wrapper"]/div[@data-element="main"]/p',
            ).extract()
        summary_text = ' '.join(map(remove_html_tags, summary))
        summary_text = clean_text_or_none(summary_text)
        if summary_text is None:
            logger.error(f'Missing summary - {response.url}')
            self.failed_urls.add(response.url)
            return
        
        yield LiteratureInfo(
            book_title=title,
            source='shmoop',
            author=author,
            summary_url=response.url,
            summary_text=summary_text,
        )

    def parse_litcharts_lit(self, response):
        # get book title
        title = response.css('h2.book-title::text').get()
        if title is None:
            logger.error(f'Missing book title - {response.url}')
            self.failed_urls.add(response.url)
            return
        title = ' '.join(title.strip().split())

        # get book author
        author = response.css('span.book-author > h3.inline::text').get()
        if author is None:
            logger.error(f'Missing author name - {response.url}')
            self.failed_urls.add(response.url)
            return
        author = ' '.join(title.strip().split())
        
        # get summary
        paragraphs = response.xpath('//p[@class="plot-text"]').extract()
        if len(paragraphs) == 0:
            logger.error(f'No summary for {response.url}')
            self.failed_urls.add(response.url)
            return
        summary_text = ' '.join(map(remove_html_tags, paragraphs))
        summary_text = clean_text_or_none(summary_text)
        if summary_text is None:
            logger.error(f'Missing summary - {response.url}')
            self.failed_urls.add(response.url)
            return

        yield LiteratureInfo(
            book_title=title,
            source='litcharts',
            author=author,
            summary_url=response.url,
            summary_text=summary_text,
        )
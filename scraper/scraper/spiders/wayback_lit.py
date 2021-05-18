# -*- coding: utf-8 -*-
from scrapy import Spider, Request
import logging

from scraper.items import LiteratureInfo
from scraper.utils import clean_text_or_none, remove_html_tags

# Remove all handlers associated with the root logger object.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    filename='runtime.log', 
    format='%(asctime)s %(message)s', 
    filemode='w',
) 

logger = logging.getLogger('waybacklogger')
logger.setLevel(logging.DEBUG) 

class WaybackLitSpider(Spider):
    name = 'wayback_lit'
    allowed_domains = ['web.archive.org']
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'ITEM_PIPELINES': {
           'scraper.pipelines.LCDataScraperWaybackPipeline': 300,
        },
    }

    def start_requests(self):
        list_filename = '/home/huangme-pop/lit_char_data/scraper/scraper/spiders/list_literatures_cached.txt'
        with open(list_filename) as in_f:
            urls = [line.strip() for line in in_f.readlines()]

        for url in urls:
            if 'www.sparknotes.com/' in url:
                yield Request(url=url, callback=self.parse_sparknotes_lit, cb_kwargs={'orig_url': url})
            elif 'www.cliffsnotes.com/' in url:
                yield Request(url=url, callback=self.parse_cliffnotes_lit, cb_kwargs={'orig_url': url})
            elif 'www.shmoop.com/' in url:
                yield Request(url=url, callback=self.parse_shmoop_lit, cb_kwargs={'orig_url': url})
            elif 'www.litcharts.com/' in url:
                yield Request(url=url, callback=self.parse_litcharts_lit, cb_kwargs={'orig_url': url})
            else:
                logger.error(f'Invalid url - {url}')

    def get_author_name(self, response, selector_paths):
        for path in selector_paths:
            author = response.css(path).get()
            if author is not None:
                return ' '.join(author.strip().split())
        return None

    def parse_sparknotes_lit(self, response, orig_url):
        # get book title
        title = response.css('h1.TitleHeader_title::text').get()
        if title is None:
            logger.error(f'Missing book title - {response.url}')
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

        # get summary
        paragraphs = response.xpath('//*[@id="plotoverview"]/p/text()').extract()
        summary_text = ' '.join(map(remove_html_tags, paragraphs))
        summary_text = clean_text_or_none(summary_text)
        if summary_text is None:
            logger.error(f'Missing summary - {response.url}')
            return

        yield LiteratureInfo(
            book_title=title,
            source='sparknotes',
            author=author,
            summary_url=response.url,
            summary_text=summary_text,
        )
    
    def parse_cliffnotes_lit(self, response, orig_url):
        # if response.url != orig_url:
        #     yield Request(
        #         url=orig_url,
        #         callback=self.parse_cliffnotes_lit,
        #         cb_kwargs={'orig_url': orig_url},
        #         dont_filter=True,
        #     )
        #     return

        # get book title
        title = response.css('div.title-wrapper > h1::text').get()
        if title is None:
            logger.error(f'Missing book title - {response.url}')
            return
        title = ' '.join(title.strip().split())

        # get book author
        author = response.css('div.title-wrapper > h2::text').get()
        if author is None:
            logger.error(f'Missing author name - {response.url}')
        else:
            author = ' '.join(author.strip().split())

        # get book summary
        paragraphs = response.css('p.litNoteText').extract()
        summary_text = ' '.join(map(remove_html_tags, paragraphs))
        summary_text = clean_text_or_none(summary_text)
        if summary_text is None:
            logger.error(f'Missing summary - {response.url}')
            return
        
        yield LiteratureInfo(
            book_title=title,
            source='cliffnotes',
            author=author,
            summary_url=response.url,
            summary_text=summary_text,
        )

    def parse_shmoop_lit(self, response, orig_url):
        # if response.url != orig_url:
        #     yield Request(
        #         url=orig_url,
        #         callback=self.parse_shmoop_lit,
        #         cb_kwargs={'orig_url': orig_url},
        #         dont_filter=True,
        #     )
        #     return

        # get book title
        title = response.css('ul.items > li:nth-child(4) > a::text').get()
        title = clean_text_or_none(title)
        if title is None:
            logger.error(f'Missing book title - {response.url}')
            return

        # get book author
        author = response.css('span.author-name::text').get()
        author = clean_text_or_none(author)
        if author is None:
            logger.error(f'Missing author name - {response.url}')
            return

        # get summary
        summary = response.xpath(
            '//div[@data-class="SHPlotOverviewSection"]/p',
        ).extract()
        summary_text = ' '.join(map(remove_html_tags, summary))
        summary_text = clean_text_or_none(summary_text)
        if summary_text is None:
            logger.error(f'Missing summary - {response.url}')
            return
        
        yield LiteratureInfo(
            book_title=title,
            source='shmoop',
            author=author,
            summary_url=response.url,
            summary_text=summary_text,
        )

    def parse_litcharts_lit(self, response, orig_url):
        # if response.url != orig_url:
        #     yield Request(
        #         url=orig_url,
        #         callback=self.parse_litcharts_lit,
        #         cb_kwargs={'orig_url': orig_url},
        #         dont_filter=True,
        #     )
        #     return

        # get book title
        title = response.css('h2.book-title::text').get()
        if title is None:
            logger.error(f'Missing book title - {response.url}')
            return
        title = ' '.join(title.strip().split())

        # get book author
        author = response.css('span.book-author > h3.inline::text').get()
        if author is None:
            logger.error(f'Missing author name - {response.url}')
            return
        author = ' '.join(title.strip().split())
        
        # get summary
        paragraphs = response.xpath('//p[@class="plot-text"]').extract()
        if len(paragraphs) == 0:
            logger.error(f'No summary for {response.url}')
        summary_text = ' '.join(map(remove_html_tags, paragraphs))
        summary_text = clean_text_or_none(summary_text)
        if summary_text is None:
            logger.error(f'Missing summary - {response.url}')
            return

        yield LiteratureInfo(
            book_title=title,
            source='litcharts',
            author=author,
            summary_url=response.url,
            summary_text=summary_text,
        )
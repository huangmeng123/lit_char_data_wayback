# -*- coding: utf-8 -*-
from scrapy import Spider, Request
import logging

from scraper.items import LiteratureInfo, CharacterInfo
from scraper.utils import remove_html_tags

SPIDER_NAME = 'shmoop'

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

class ShmoopSpider(Spider):
    name = SPIDER_NAME
    allowed_domains = ['www.shmoop.com']
    start_urls = ['https://www.shmoop.com/study-guides/literature']
    custom_settings = {
        # 'DOWNLOAD_DELAY': 0.1,
        'ITEM_PIPELINES': {
           'scraper.pipelines.LCDataScraperProdPipeline': 300,
        },
    }

    def parse(self, response):
        first = int(response.xpath(
            '//ul[@class="items pages-items"]/li[1]/*/span[2]/text()',
        ).get())
        last = int(response.xpath(
            '//ul[@class="items pages-items"]/li[last()-1]/*/span[2]/text()',
        ).get())
        for i in range(first, last+1):
            yield Request(
                url=f'https://www.shmoop.com/study-guides/literature/index/?p={i}',
                callback=self.parse_page,
            )

    def parse_page(self, response):
        book_selectors = response.xpath('//a[@class="details"]')
        for selector in book_selectors:
            url = selector.xpath('./@href').get()
            book_title = selector.xpath('./div[@class="item-info"]/text()').get().strip()
            full_url = response.urljoin(url)
            yield Request(
                url=full_url,
                callback=self.parse_book,
                cb_kwargs={
                    'book_title': book_title,
                },
                dont_filter=True,
            )
    
    def parse_book(self, response, book_title):
        author = response.xpath(
            '//span[@class="author-name"]/text()',
        ).get().strip()

        summary_url = response.xpath(
            '//div[@class="nav-menu"]/ul/li'
            '/a[contains(text(), "Summary")]/@href',
        ).get()

        if summary_url is None or len(summary_url) == 0:
            logger.error(f'No summary - {response.url}')
            summary_url = None
        else:
            summary_url = response.urljoin(summary_url)
            yield Request(
                url=summary_url,
                callback=self.parse_summary,
                cb_kwargs={
                    'book_title': book_title,
                },
                dont_filter=True,
            )

        character_list_url = response.xpath(
            '//div[@class="nav-menu"]/ul/li'
            '/a[contains(text(), "Characters")]/@href',
        ).get()
        if character_list_url is None or len(character_list_url) == 0:
            logger.error(f'No summary - {response.url}')
            character_list_url = None
        else:
            character_list_url = response.urljoin(character_list_url)
            yield Request(
                url=character_list_url,
                callback=self.parse_character_list,
                cb_kwargs={
                    'book_title': book_title,
                },
                dont_filter=True,
            )

        # report literature info
        yield LiteratureInfo(            
            book_title=book_title,
            source=SPIDER_NAME,
            author=author,
            book_url=response.url,
            summary_url=summary_url,
            character_list_url=character_list_url,
        )

    def parse_summary(self, response, book_title):
        summary = response.xpath(
            '//div[@class="content-wrapper"]/div[2]/p',
        ).extract()
        summary_text = ' '.join('\n'.join(
            map(remove_html_tags, summary),
        ).split())
        yield LiteratureInfo(
            book_title=book_title,
            source=SPIDER_NAME,
            summary_url=response.url,
            summary_text=summary_text,
        )

    def parse_character_list(self, response, book_title):
        character_urls = response.xpath(
            '//div[@class="content-wrapper"]/div[2]/h3/a/@href',
        ).extract()
        for i, url in enumerate(character_urls):
            character_url = response.urljoin(url)
            yield Request(
                url=character_url,
                callback=self.parse_character,
                cb_kwargs={
                    'book_title': book_title,
                    'character_order': i,
                },
                dont_filter=True,
            )

    def __parse_major_character(self, response, character_name, character_order):
        cdescription = response.xpath(
            '//div[@class="content-wrapper"]/div[2]/p[count(preceding::h3)=1]',
        ).extract()
        cdescription_text = ' '.join('\n'.join(
            map(remove_html_tags, cdescription),
        ).split())
        if len(cdescription_text) == 0:
            logger.error(f'No character description - {response.url}')
            cdescription_text = None

        canalysis = response.xpath(
            '//div[@class="content-wrapper"]/div[2]/p',
        ).extract()
        canalysis_text = ' '.join('\n'.join(
            map(remove_html_tags, canalysis),
        ).split())
        if len(canalysis_text) == 0:
            logger.error(f'No character analysis - {response.url}')
            canalysis_text = None

        return [{
            'name': character_name,
            'order': character_order,
            'description_text': cdescription_text,
            'analysis_text': canalysis_text,
        }]

    def __parse_minor_character(self, response):
        num_characters = len(response.xpath(
            '//div[@class="content-wrapper"]/div[2]/h3',
        ))

        characters = []
        for i in range(num_characters):
            selector = response.xpath('//div[@class="content-wrapper"]/div[2]')
            cname = selector.xpath(f'./h3[{i+1}]/text()').get().strip()
            cdescription = selector.xpath(
                f'./p[count(preceding::h3)={i+2}]',
            ).extract()
            cdescription_text = ' '.join('\n'.join(
                map(remove_html_tags, cdescription),
            ).split())
            characters.append({
                'name': cname,
                'order': 100,
                'description_text': cdescription_text,
                'analysis_text': None,
            })
        
        return characters

    def parse_character(self, response, book_title, character_order):
        cname = response.xpath('//h2[@class="title"]/text()').get().strip()

        if cname == 'Minor Characters':
            characters = self.__parse_minor_character(response)
        else:
            characters = self.__parse_major_character(
                response,
                cname,
                character_order
            )

        for character in characters:
            yield CharacterInfo(
                character_name=character['name'],
                book_title=book_title,
                source=SPIDER_NAME,
                character_order=character['order'],
                description_url=(
                    response.url
                    if character['description_text'] is not None
                    else None
                ),
                description_text=character['description_text'],
                analysis_url=(
                    response.url
                    if character['analysis_text'] is not None
                    else None
                ),
                analysis_text=character['analysis_text'],
            )


# -*- coding: utf-8 -*-
from scrapy import Spider, Request
import logging

from scraper.items import LiteratureInfo, CharacterInfo

# Remove all handlers associated with the root logger object.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    filename='runtime.log', 
    format='%(asctime)s %(message)s', 
    filemode='w',
) 

logger = logging.getLogger('sparknoteslogger')
logger.setLevel(logging.DEBUG) 

class SparknotesSpider(Spider):
    name = 'sparknotes'
    allowed_domains = ['www.sparknotes.com']
    start_urls = ['http://www.sparknotes.com/lit/']
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        # 'ITEM_PIPELINES': {
        #    'scrapynotes.pipelines.LCDataScraperProdPipeline': 300,
        # },
    }

    def parse(self, response):
        book_card_selectors = response.css('.hub-AZ-list__card')
        for selector in book_card_selectors:
            title = selector.css(
                '.hub-AZ-list__card__title__link::text',
            ).get()
            url = selector.css(
                '.hub-AZ-list__card__title__link::attr(href)',
            ).get()
            author = selector.css(
                '.hub-AZ-list__card__secondary::text',
            ).get()
            
            full_url = response.urljoin(url)

            yield Request(
                url=full_url,
                callback=self.parse_book,
                cb_kwargs={
                    'book_title': title,
                    'author': author,
                },
                dont_filter=True,
            )

    def parse_book(self, response, book_title, author):
        subsection_selectors = response.xpath(
            '//div[@class="landing-page__umbrella__section"]/ul/li',
        )

        # get summary url
        summary_url = subsection_selectors.xpath(
            './a[text()[contains(., "Plot Overview")]]/@href',
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

        # get character list url
        character_list_url = subsection_selectors.xpath(
            './a[text()[contains(., "Character List")]]/@href',
        ).get()

        if character_list_url is None or len(character_list_url) == 0:
            char_list_url_xpath = (
                '//a[@class["landing-page__umbrella__header__title--is-link"] '
                'and text()[contains(., "Characters")]]/@href'
            )
            character_list_url = response.xpath(char_list_url_xpath).get()
        
        if character_list_url is None or len(character_list_url) == 0:
            char_list_url_xpath = (
                '//a[@class["landing-page__umbrella__header__title--is-link"] '
                'and text()[contains(., "Character List")]]/@href'
            )
            character_list_url = response.xpath(char_list_url_xpath).get()

        if character_list_url is None or len(character_list_url) == 0:
            logger.error(f'No character list - {response.url}')
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
            source='sparknotes',
            author=author,
            book_url=response.url,
            summary_url=summary_url,
            character_list_url=character_list_url,
        )

    def parse_summary(self, response, book_title):
        summary = response.xpath('//*[@id="plotoverview"]/p/text()').extract()

        if len(summary) == 0:
            logger.error(f'Empty summary content - {response.url}')

        yield LiteratureInfo(
            book_title=book_title,
            source='sparknotes',
            summary_url=response.url,
            summary_text=' '.join('\n'.join(summary).split()),
        )

    def parse_character_list(self, response, book_title):
        character_xpath = '//li[@class="mainTextContent__list-content__item"]'
        character_selectors = response.xpath(character_xpath)

        for i, selector in enumerate(character_selectors):
            cname = selector.xpath('./h3/text()').get()
            cdescription = selector.xpath(f'./p/text()').extract()
            cdescription_text = ' '.join((''.join(cdescription)).split())

            logger.info(
                f'\nCharacter Name: {cname}\n'
                f'Character Order: {i}\n'
                f'Description: {cdescription_text}\n'
            )

            yield CharacterInfo(
                character_name=cname,
                book_title=book_title,
                source='sparknotes',
                character_order=i,
                description_url=response.url,
                description_text=cdescription_text,
            )

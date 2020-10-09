# -*- coding: utf-8 -*-
'''cSpell:disable
This Scrapy module provides parsers for cliffsnotes.com website.
'''
import string
import logging

from scrapy import Request, Spider

from scraper.items import LiteratureInfo, CharacterInfo
from scraper.utils import extract_paragraphs, extract_text
from scraper.utils import remove_html_tags, clean_text_or_none

SPIDER_NAME = 'cliffnotes'

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

class CliffsnotesSpider(Spider):
    '''Scrapy spider class for extracting notes from cliffsnotes.com website.'''

    name = SPIDER_NAME
    allowed_domains = ['cliffsnotes.com']
    start_urls = [
        'https://www.cliffsnotes.com/literature?filter=ShowAll&sort=TITLE',
    ]
    custom_settings = {
        'DOWNLOAD_DELAY': 0.1,
        'ITEM_PIPELINES': {
           'scraper.pipelines.LCDataScraperProdPipeline': 300,
        },
    }

    def parse(self, response):
        '''Parse index to yield book urls'''
        books = response.css('div.note-name').xpath('./ancestor::a[1]')
        for book in books:
            title = book.xpath('./div/div[1]/h4/text()').get()
            title = clean_text_or_none(title)
            if title is None: continue
            
            author = book.xpath('./div/div[1]/h4/text()').get()
            author = clean_text_or_none(author)
            
            href = book.attrib['href']
            url = response.urljoin(href)
            
            # Initialize list fields so we can directly append dictionaries to them
            book = LiteratureInfo(
                book_title=title,
                source=SPIDER_NAME,
                book_url=url,
                author=author,
            )
            yield Request(
                url=url,
                callback=self.parse_book,
                cb_kwargs={
                    'book': book,
                },
            )

    def parse_book(self, response, book):
        # First get the nodes in the nav that point to various sections
        url = response.url
        ignored = (
            "/a/aeneid" in url,
            "/o/100-years-of-solitude" in url,
        )

        if any(ignored): return

        nav_selector = response.xpath(
            '//section[@class="secondary-navigation"]/ul/li/a',
        )

        # handle "summary" section
        summary_selector = nav_selector.xpath(
            './/span[re:test(., "(Book|Play|Poem|Story) Summary")]',
        )
        if summary_selector:
            summary_href = summary_selector.xpath('./../@href').get()
            summary_url = response.urljoin(summary_href)
            book['summary_url'] = summary_url
            yield Request(
                url=summary_url,
                callback=self.parse_summary,
                cb_kwargs={
                    'book': book,
                },
                dont_filter=True,
            )
        
        # handle character description section
        charlist = nav_selector.xpath(
            './/span[starts-with(., "Character List") and '
            'not(contains(., "Analysis"))]',
        )
        if charlist:
            charlist_href = charlist.xpath('./../@href').get()
            charlist_url = response.urljoin(charlist_href)
            book['character_list_url'] = charlist_url
            yield Request(
                url=charlist_url,
                callback=self.parse_character_list,
                cb_kwargs={
                    'book': book,
                },
                dont_filter=True,
            )

        yield book

    def parse_summary(self, response, book):
        paragraphs = response.css('p.litNoteText').extract()
        summary_text = ' '.join(map(remove_html_tags, paragraphs))
        book['summary_text'] = clean_text_or_none(summary_text)
        yield book

    def parse_character_list(self, response, book):
        url = response.url
        characters = response.css('article.copy > p.litNoteText > b,strong')
        # some have p.litNoteTextHeading as class
        heading = False
        if not characters:
            characters = response.css('article.copy > p.litNoteTextHeading')
            if characters:
                heading = True

        if not characters:
            raise NotImplementedError(f'Unable to find characters in {response.url}')

        for i, char in enumerate(characters):
            name = extract_text(char).strip()
            if not name: continue

            if heading:
                description_node = char.xpath('./following-sibling::p[1]')
            else:
                description_node = char.xpath(
                    './../descendant-or-self::*[self::p|self::i]',
                )
            description = map(remove_html_tags, description_node.extract())
            description = ' '.join(description)
            description = clean_text_or_none(description)
            logger.debug(description)

            yield CharacterInfo(
                character_name=name,
                book_title=book['book_title'],
                source=SPIDER_NAME,
                character_list_url=url,
                character_order=i,
                description_url=url,
                description_text=description,
            )

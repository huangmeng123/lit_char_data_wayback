# -*- coding: utf-8 -*-
from scrapy import Spider, Request, signals
import logging
import re, string, json, os

from scraper.items import CharacterInfo
from scraper.utils import extract_paragraphs, extract_text
from scraper.utils import clean_text_or_none, remove_html_tags
from scrapy.utils.log import configure_logging


puncts = set(string.punctuation)

_ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
_STATIC_DIR = os.path.join(_ROOT_DIR, 'static')
_OUTPUT_DIR = os.path.join(_ROOT_DIR, 'output')
_INPUT_DIR = os.path.join(_ROOT_DIR, 'input')

ALL_URLS_FILENAME = os.path.join(_STATIC_DIR, 'list_characters_cached.txt')
LITCHARTS_ADJUSTMENT_FILENAME = os.path.join(_STATIC_DIR, 'litcharts_adjustment.json')

INPUT_URLS_FILENAME = os.path.join(_INPUT_DIR, 'list_characters_retry.txt')
OUTPUT_URLS_FILENAME = os.path.join(_OUTPUT_DIR, 'list_characters_failed.txt')

LOG_PATH = os.path.join(_OUTPUT_DIR, 'wayback_char_runtime.log')


LOG_ENABLED = False
# Disable default Scrapy log settings.
configure_logging(install_root_handler=False)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
_ch = logging.FileHandler(LOG_PATH, 'w+')
_ch.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
logger.addHandler(_ch)

class WaybackCharSpider(Spider):
    name = 'wayback_char'
    allowed_domains = ['web.archive.org']
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'ITEM_PIPELINES': {
           'scraper.pipelines.LCDataScraperDatabasePipeline': 300,
        },
    }

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(WaybackCharSpider, cls).from_crawler(crawler, *args, **kwargs)
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

        with open(LITCHARTS_ADJUSTMENT_FILENAME) as in_f:
            self.litcharts_adjustment = json.load(in_f)
        
        self.failed_urls = set()
        
        for url in urls:
            yield Request(
                url=url,
                callback=self.validate_response,
                cb_kwargs={'orig_url': url},
            )

    def spider_closed(self, spider):
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
            for result in self.parse_sparknotes_char(response):
                yield result
        elif 'www.cliffsnotes.com/' in url:
            for result in self.parse_cliffnotes_char(response):
                yield result
        elif 'www.shmoop.com/' in url:
            for result in self.parse_shmoop_char(response):
                yield result
        elif 'www.litcharts.com/' in url:
            if url.endswith('/characters'):
                for result in self.parse_litcharts_minor_char(response):
                    yield result
            else:
                for result in self.parse_litcharts_major_char(response):
                    yield result
        else:
            logger.error(f'Invalid url - {url}')

    def parse_sparknotes_char(self, response):
        # get book title
        title = response.css('h1.TitleHeader_title::text').get()
        title = clean_text_or_none(title)
        if title is None:
            logger.error(f'Missing book title - {response.url}')
            return

        character_xpath = '//li[@class="mainTextContent__list-content__item"]'
        character_selectors = response.xpath(character_xpath)

        for i, selector in enumerate(character_selectors):
            cname = selector.xpath('./h3/text()').get().strip()
            paragraphs = selector.xpath(f'./p/text()').extract()
            cdescription_text = ' '.join(map(remove_html_tags, paragraphs))
            cdescription_text = clean_text_or_none(cdescription_text)

            if (
                cname == 'Unnamed narrator' and
                not cdescription_text.startswith(
                    'Husband of both Lady Ligeia and Lady Rowena'
                )
            ):
                continue

            yield CharacterInfo(
                character_name=cname,
                book_title=title,
                source='sparknotes',
                character_order=i,
                character_list_url=response.url,
                description_url=response.url,
                description_text=cdescription_text,
            )

    def parse_cliffnotes_char(self, response):
        url = response.url

        # get book title
        title = response.css('div.title-wrapper > h1::text').get()
        title = clean_text_or_none(title)
        if title is None:
            logger.error(f'Missing book title - {url}')
            return

        characters = response.css(
            'article.copy > p > b,'
            'article.copy > p > strong'
        )

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
                book_title=title,
                source='cliffnotes',
                character_list_url=url,
                character_order=i,
                description_url=url,
                description_text=description,
            )

    def __parse_shmoop_major_char(self, response, character_name):
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
            'description_text': cdescription_text,
            'analysis_text': canalysis_text,
        }]

    def __parse_shmoop_minor_char(self, response):
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

    def shmoop_find_correct_title(self, response):
        title = response.css('ul.items > li:nth-child(4) > a::text').get()
        if title is not None: return title

        content = response.css('meta[name="title"]::attr(content)').get()
        content = clean_text_or_none(content)
        if content is None: return None
        pattern = r'.*? in (.*) \| Shmoop$'
        title_candidates = set()
        while True:
            capture = re.search(pattern, content)
            if capture is None: break
            title = capture.group(1)
            title_candidates.add(title)
            pattern = r'.*? in ' + pattern

        if 'Oliver Twist' in title_candidates: return 'Oliver Twist'

        content = response.css('meta[name="description"]::attr(content)').get()
        content = clean_text_or_none(content)
        if content is None: return None
        pattern = r'.*? from (.*) by'
        prefix = r''
        while True:
            surfix = r''
            while True:
                capture = re.search(prefix + pattern + surfix, content)
                if capture is None: break
                title = capture.group(1)
                logger.info(title)
                logger.info('|'.join(title_candidates))
                if title in title_candidates: return title
                surfix += r' .* by'
            if len(surfix) == 0: break
            prefix = r'.*? from ' + prefix
        
        return None

    def parse_shmoop_char(self, response):
        # get book title
        title = self.shmoop_find_correct_title(response)
        title = clean_text_or_none(title)
        if title is None:
            logger.error(f'Missing book title - {response.url}')
            return

        # get character info
        cname = response.xpath('//h2[@class="title"]/text()').get().strip()

        if cname == 'Minor Characters':
            characters = self.__parse_shmoop_minor_char(response)
        else:
            characters = self.__parse_shmoop_major_char(response, cname)

        for character in characters:
            if (
                character['description_text']
                    .startswith(
                        'George Hurstwood Jr. is Hurstwood\'s son.'
                    )
            ): continue
            yield CharacterInfo(
                character_name=character['name'],
                book_title=title,
                source='shmoop',
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

    def parse_litcharts_major_char(self, response):
        # get book title
        title = response.css('h2.book-title::text').get()
        title = clean_text_or_none(title)
        if title is None:
            logger.error(f'Missing book title - {response.url}')
            return

        # get character name
        char_name = response.css('span.component-title::text').get()
        char_name = clean_text_or_none(char_name)
        if char_name is None:
            logger.error(f'Missing character name - {response.url}')
            return

        # get character description
        paragraphs = response.xpath(
            '//div[@class="highlightable-content"]',
        ).extract()
        if len(paragraphs) == 0:
            logger.error(
                f'No description for {response.url}',
            )
            return
        description_text = ' '.join(map(remove_html_tags, paragraphs))
        description_text = clean_text_or_none(description_text)

        char_info = CharacterInfo(
            character_name=char_name,
            book_title=title,
            source='litcharts',
            description_url=response.url,
            description_text=description_text,
        )

        if char_name in self.litcharts_adjustment:
            for adjusted_char_name in self.litcharts_adjustment[char_name]:
                char_info['character_name'] = adjusted_char_name
                yield char_info

        yield char_info

    def parse_litcharts_minor_char(self, response):
        # get book title
        title = response.css('h2.book-title::text').get()
        title = clean_text_or_none(title)
        if title is None:
            logger.error(f'Missing book title - {response.url}')
            return

        # parse minor characters
        minor_character_nodes = response.xpath(
            '//div[@class="character readable"]',
        )
        for node in minor_character_nodes:
            name = node.xpath('.//div["name"]/text()').get()
            name = clean_text_or_none(name)
            if name is None:
                logger.error(
                    f'Missing character name - {response.url}',
                )
                continue

            classes = 'no-inline-characters no-inline-symbols no-inline-terms'
            paragraphs = node.xpath(f'.//div[@class="{classes}"]').extract()
            if len(paragraphs) == 0:
                logger.error(
                    f'No description for minor character {name} - {response.url}',
                )
                continue
            description_text = ' '.join(map(remove_html_tags, paragraphs))
            description_text = clean_text_or_none(description_text)
            yield CharacterInfo(
                character_name=name,
                book_title=title,
                source='litcharts',
                character_list_url=response.url,
                description_url=response.url,
                description_text=description_text,
                character_order=100,
            )
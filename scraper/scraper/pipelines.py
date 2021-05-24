# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

# useful for handling different item types with a single interface
import psycopg2
from scraper.items import LiteratureInfo, CharacterInfo
from typing import BinaryIO

class DatabaseConnection(object):
    def __init__(self, database='lcdata-dev'):
        hostname = 'localhost'
        username = 'test'
        password = 'test'
        self.conn = psycopg2.connect(
            host=hostname,
            user=username,
            password=password,
            dbname=database,
        )
        self.cur = self.conn.cursor()

    def close(self):
        self.cur.close()
        self.conn.close()

    def write(self, table_name, primary_fields, optional_fields):
        prim_keys = tuple(primary_fields.keys())
        opt_keys = tuple(optional_fields.keys())
        keys = prim_keys + opt_keys

        prim_vals = tuple(primary_fields.values())
        opt_vals = tuple(optional_fields.values())
        vals = prim_vals + opt_vals

        column_list = ','.join(keys)
        value_list = ','.join(['%s' for _ in vals])
        conflict_targets = ','.join(prim_keys)
        overwrites = ','.join([f'{key} = EXCLUDED.{key}' for key in opt_keys])

        query = (
            f'INSERT INTO {table_name} ({column_list}) VALUES ({value_list}) '
            f'ON CONFLICT ({conflict_targets}) '
            f'DO UPDATE SET {overwrites};'
        )

        self.cur.execute(query, vals)
        self.conn.commit()

    def read(self, table_name, primary_fields, target_keys):
        filter_template = ' AND '.join(
            [f'{fkey}=%s' for fkey, fvalue in primary_fields.items()],
        )
        filter_values = tuple([fvalue for _, fvalue in primary_fields])
        target_template = ','.join(target_keys)
        query = (
            f'SELECT {target_template} FROM {table_name} '
            f'WHERE {filter_template};'
        )

        self.cur.execute(query, filter_values)
        return self.cur.fetchall()


LIT_PRIMS = ['book_title', 'source']
CHAR_PRIMS = ['character_name', 'book_title', 'source']

DIR_PATH = '/home/huangme-pop/lit_char_data/scraper/scraper/spiders'
URLS_FILENAME = f'{DIR_PATH}/list_characters_cached.txt'

class LCDataScraperPipeline(object):
    _db: DatabaseConnection

    def close_spider(self, spider):
        self._db.close()

    def process_item(self, item, spider):
        if isinstance(item, LiteratureInfo):
            self.process_literature_info(item)

        elif isinstance(item, CharacterInfo):
            self.process_character_info(item)

        return item

    def process_literature_info(self, item: LiteratureInfo):
        data = list(item.items())
        primary_fields = list(filter(lambda e: e[0] in LIT_PRIMS, data))
        primary_fields = {key: val for key, val in primary_fields}
        optional_fields = list(filter(lambda e: e[0] not in LIT_PRIMS, data))
        optional_fields = {key: val for key, val in optional_fields}
        self._db.write(
            table_name='literatures',
            primary_fields=primary_fields,
            optional_fields=optional_fields,
        )

    def process_character_info(self, item: CharacterInfo):
        data = list(item.items())
        primary_fields = list(filter(lambda e: e[0] in CHAR_PRIMS, data))
        primary_fields = {key: val for key, val in primary_fields}
        optional_fields = list(filter(lambda e: e[0] not in CHAR_PRIMS, data))
        optional_fields = {key: val for key, val in optional_fields}
        self._db.write(
            table_name='characters',
            primary_fields=primary_fields,
            optional_fields=optional_fields,
        )

class LCDataScraperProdPipeline(LCDataScraperPipeline):
    def open_spider(self, spider):
        self._db = DatabaseConnection(database='lcdata')

class LCDataScraperDevPipeline(LCDataScraperPipeline):
    def open_spider(self, spider):
        self._db = DatabaseConnection(database='lcdata-dev')

class LCDataScraperWaybackPipeline(LCDataScraperPipeline):
    def open_spider(self, spider):
        self._db = DatabaseConnection(database='lcdata-wayback')

class LCDataScraperWaybackFinalPipeline(LCDataScraperPipeline):
    def open_spider(self, spider):
        self._db = DatabaseConnection(database='lcdata-wayback-final')

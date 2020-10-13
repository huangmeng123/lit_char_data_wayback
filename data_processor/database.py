import psycopg2

from data_schema import Literature, Character 

class DatabaseConnection(object):
    def __init__(self, database='lcdata-dev'):
        hostname = 'localhost'
        username = 'huangme'
        password = 'huangme'
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

    def read_literature_data(self):
        query = (
            'SELECT book_title, source, book_url, author, summary_url, '
            'summary_text, character_list_url FROM literatures '
            'WHERE TRUE'
            "summary_text IS NOT NULL AND summary_text <> '' "
            "AND source <> 'gradesaver' "
            'ORDER BY source, book_title;'
        )

        self.cur.execute(query)
        literatures = []
        ind = 0
        for row in self.cur.fetchall():
            literatures.append(Literature(ind, *row))
            ind += 1
        return literatures

    def read_character_data(self):
        query = (
            'SELECT character_name, book_title, source, character_list_url, '
            'character_order, description_url, description_text, '
            'analysis_url, analysis_text FROM characters '
            'WHERE TRUE '
            "AND description_text IS NOT NULL AND description_text <> '' "
            "AND character_name <> 'Major'"
            "AND character_name <> 'Minor'"
            "AND character_name <> 'Major Characters'"
            "AND character_name <> 'Minor Characters'"
            "AND source <> 'gradesaver' "
            'ORDER BY source, book_title, character_order, character_name;'
        )

        self.cur.execute(query)
        characters = []
        for row in self.cur.fetchall():
            characters.append(Character(*row))
        return characters
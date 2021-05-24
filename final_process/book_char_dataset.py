from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from .database_util import CharacterInfoWithMaskedDescription, DatabaseConnection
from .database_util import BookKey, CharKey
from .database_util import BookInfo, CharacterInfo
from .common_util import read_jsonl, write_jsonl
from .text_diff_tool import IndRange, TextDiffTool

class BookCharDataset(object):
    book_lookup: Dict[BookKey, Any]
    char_lookup: Dict[CharKey, Any]

    @property
    def num_books(self) -> int:
        return len(self.book_lookup)

    @property
    def num_unique_books(self) -> int:
        uniq_books: Set[str] = set()
        for book_title, _ in self.book_lookup.keys():
            uniq_books.add(book_title)
        return len(uniq_books)

    @property
    def num_characters(self) -> int:
        return len(self.char_lookup)

    def filter_by_char_keys(self, char_keys: List[CharKey]):
        book_keys: List[BookKey] = list(set([
            (title, source) for title, source, _ in char_keys
        ]))
        self.book_lookup = {
            book_key: self.book_lookup[book_key]
            for book_key in book_keys
        }
        self.char_lookup = {
            char_key: self.char_lookup[char_key]
            for char_key in char_keys
        }


class BasicBookCharDataset(BookCharDataset):
    book_lookup: Dict[BookKey, BookInfo]
    char_lookup: Dict[CharKey, CharacterInfo]

    def __init__(
        self,
        books: List[BookInfo],
        characters: List[CharacterInfo],
    ):
        self.book_lookup = {book.book_key: book for book in books}
        self.char_lookup = {char.char_key: char for char in characters}
    
    @classmethod
    def load_from_database(
        cls,
        db_conn: DatabaseConnection,
    ) -> BasicBookCharDataset:
        books = db_conn.read_book_info()
        characters = db_conn.read_character_info()
        return cls(books, characters)

    @classmethod
    def load_from_jsonl(cls, filename: str) -> BasicBookCharDataset:
        data: List[dict] = read_jsonl(filename)
        
        books: List[BookInfo] = []
        book_keys: Set[BookKey] = set()
        characters: List[CharacterInfo] = []
        for d in data:
            book_key: BookKey = (d['book_title'], d['source'])
            if book_key not in book_keys:
                books.append(BookInfo(
                    book_title=d['book_title'],
                    source=d['source'],
                    summary=d['summary'],
                ))
                book_keys.add(book_key)
            
            characters.append(CharacterInfo(
                book_title=d['book_title'],
                source=d['source'],
                character_name=d['character_name'],
                description=d['description'],
            ))
        
        return cls(books, characters)

    def export_to_jsonl(self, filename: str):
        book_char_data = []
        for char_info in self.char_lookup.values():
            book_key = char_info.book_key
            book_info = self.book_lookup[book_key]
            book_char_data.append({
                'book_title': book_info.book_title,
                'source': book_info.source,
                'character_name': char_info.character_name,
                'summary': book_info.summary,
                'description': char_info.description,
            })
        write_jsonl(filename, book_char_data)

    def replace_keys(
        self,
        book_key_replacement: Dict[BookKey, BookKey],
        char_key_replacement: Dict[CharKey, CharKey],
    ):
        new_book_lookup: Dict[BookKey, BookInfo] = {}
        for book_key, book_info in self.book_lookup.items():
            new_book_key = book_key_replacement.get(
                book_key, book_key
            )
            book_info.book_title = new_book_key[0]
            book_info.source = new_book_key[1]
            new_book_lookup[new_book_key] = book_info

        new_char_lookup: Dict[CharKey, CharacterInfo] = {}
        for char_key, char_info in self.char_lookup.items():
            new_char_key = char_key_replacement.get(
                char_key, char_key
            )
            char_info.book_title = new_char_key[0]
            char_info.source = new_char_key[1]
            char_info.character_name = new_char_key[2]
            new_char_lookup[new_char_key] = char_info

        self.book_lookup = new_book_lookup
        self.char_lookup = new_char_lookup

    def adjust_description(
        self,
        change_lookup: Dict[CharKey, List[Tuple[IndRange, str]]],
    ):
        for char_key, char_info in self.char_lookup.items():
            changes = change_lookup.get(char_key, [])
            new_description = TextDiffTool.restore_text(
                char_info.description, changes
            )
            self.char_lookup[char_key].description = new_description



class FinalBookCharDataset(object):
    book_lookup: Dict[BookKey, BookInfo]
    char_lookup: Dict[CharKey, CharacterInfoWithMaskedDescription]

    def __init__(
        self,
        books: List[BookInfo],
        characters: List[CharacterInfoWithMaskedDescription],
    ):
        self.book_lookup = {book.book_key: book for book in books}
        self.char_lookup = {char.char_key: char for char in characters}

    @classmethod
    def load_from_jsonl(cls, filename: str) -> FinalBookCharDataset:
        data: List[dict] = read_jsonl(filename)
        
        books: List[BookInfo] = []
        book_keys: Set[BookKey] = set()
        characters: List[CharacterInfoWithMaskedDescription] = []
        for d in data:
            book_key: BookKey = (d['book_title'], d['source'])
            if book_key not in book_keys:
                books.append(BookInfo(
                    book_title=d['book_title'],
                    source=d['source'],
                    summary=d['summary'],
                ))
                book_keys.add(book_key)
            
            characters.append(CharacterInfoWithMaskedDescription(
                book_title=d['book_title'],
                source=d['source'],
                character_name=d['character_name'],
                description=d['description'],
                masked_description=d['masked_description'],
            ))
        
        return cls(books, characters)

    def export_to_jsonl(self, filename: str):
        book_char_data = []
        for char_info in self.char_lookup.values():
            book_key = char_info.book_key
            book_info = self.book_lookup[book_key]
            book_char_data.append({
                'book_title': book_info.book_title,
                'source': book_info.source,
                'character_name': char_info.character_name,
                'summary': book_info.summary,
                'description': char_info.description,
                'masked_description': char_info.masked_description,
            })
        write_jsonl(filename, book_char_data)
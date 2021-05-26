from __future__ import annotations

from typing import Any, Dict, Optional
from dataclasses import dataclass
import ast

from .database_util import BookKey, CharKey
from .common_util import read_json

@dataclass
class KeyTranslator(object):
    new_to_old_book_key_mapping: Dict[BookKey, BookKey]
    old_to_new_book_key_mapping: Dict[BookKey, BookKey]
    new_to_old_char_key_mapping: Dict[CharKey, CharKey]
    old_to_new_char_key_mapping: Dict[CharKey, CharKey]

    @staticmethod
    def load_mapping(filename: str) -> dict:
        mapping: Dict[str, str] = read_json(filename)
        return {
            ast.literal_eval(key): ast.literal_eval(val)
            for key, val in mapping.items()
        }

    @classmethod
    def load_from_json_files(
        cls,
        new_to_old_book_key_mapping_filename: str,
        old_to_new_book_key_mapping_filename: str,
        new_to_old_char_key_mapping_filename: str,
        old_to_new_char_key_mapping_filename: str,
    ) -> KeyTranslator:
        return cls(
            cls.load_mapping(new_to_old_book_key_mapping_filename),
            cls.load_mapping(old_to_new_book_key_mapping_filename),
            cls.load_mapping(new_to_old_char_key_mapping_filename),
            cls.load_mapping(old_to_new_char_key_mapping_filename),
        )

    def to_new_book_key(self, old_book_key: BookKey) -> Optional[BookKey]:
        return self.old_to_new_book_key_mapping.get(old_book_key, None)
    
    def to_old_book_key(self, new_book_key: BookKey) -> Optional[BookKey]:
        return self.new_to_old_book_key_mapping.get(new_book_key, None)

    def to_new_char_key(self, old_char_key: CharKey) -> Optional[CharKey]:
        return self.old_to_new_char_key_mapping.get(old_char_key, None)
    
    def to_old_char_key(self, new_char_key: CharKey) -> Optional[CharKey]:
        return self.new_to_old_char_key_mapping.get(new_char_key, None)
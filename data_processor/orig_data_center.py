from typing import List, Dict, Tuple

import json
import csv

from .database import DatabaseConnection
from .orig_utils import OrigLiteratureInfo, OrigCharacterInfo
from .orig_utils import OrigBook, OrigLitKey, OrigCharKey

class OrigBookDataCenter(object):
    def __init__(
        self,
        literatures: List[OrigLiteratureInfo],
        characters: List[OrigCharacterInfo],
    ):
        self.literatures: Dict[OrigLitKey, OrigLiteratureInfo] = {}
        for lit in literatures:
            self.literatures[lit.key] = lit

        self.characters: Dict[OrigCharKey, OrigCharacterInfo] = {}
        for char in characters:
            if char.lit_key in self.literatures:
                if char.key[2] == '': continue
                self.characters[char.key] = char

        self.orig_books: Dict[int, OrigBook] = {}
        for lit in self.literatures.values():
            book = OrigBook(
                book_info=lit,
                characters={},
            )
            self.orig_books[lit.book_ind] = book
        for char in self.characters.values():
            ind = self.literatures[char.lit_key].book_ind
            book = self.orig_books[ind]
            book.characters[char.character_name] = char

    @classmethod
    def build_from_dev_database(cls):
        db = DatabaseConnection()
        literatures = db.read_literature_data()
        characters = db.read_character_data()
        db.close()
        return cls(
            literatures=literatures,
            characters=characters,
        )

    @classmethod
    def build_from_database(cls):
        db = DatabaseConnection(database='lcdata')
        literatures = db.read_literature_data()
        characters = db.read_character_data()
        db.close()
        return cls(
            literatures=literatures,
            characters=characters,
        )

    @classmethod
    def build_from_wayback_database(cls):
        db = DatabaseConnection(database='lcdata-wayback')
        literatures = db.read_literature_data()
        characters = db.read_character_data()
        db.close()
        return cls(
            literatures=literatures,
            characters=characters,
        )

    @classmethod
    def build_from_file(cls, filename: str):
        with open(filename) as json_file:
            data: Dict[str, List[dict]] = json.load(json_file)
            literatures = [
                OrigLiteratureInfo(**lit)
                for lit in data['literatures']
            ]
            characters = [
                OrigCharacterInfo(**char)
                for char in data['characters']
            ]

        return cls(
            literatures=literatures,
            characters=characters,
        )

    def export_to_file(self, filename: str):
        data = {
            'literatures': [
                lit.to_dict() for lit in self.literatures.values()
            ],
            'characters': [
                char.to_dict() for char in self.characters.values()
            ],
        }
        with open(filename, 'w') as outfile:
            json.dump(data, outfile)

    @property
    def num_lits(self) -> int:
        return len(self.literatures)

    @property
    def num_chars(self) -> int:
        return len(self.characters)

    def __len__(self) -> int:
        return len(self.orig_books)

    def __getitem__(self, ind: int) -> OrigBook:
        return self.orig_books[ind]

    def indices(self) -> List[int]:
        return list(self.orig_books.keys())

    def validate(self):
        # validate each book
        for book in self.orig_books.values():
            book.validate()

        # check if the book index is consistent
        inds = list(self.orig_books.keys())
        assert(len(inds) == len(set(inds)))
        for ind in range(max(inds)+1):
            assert(ind in self.orig_books)

    def get_all_summaries_inorder(self) -> List[str]:
        inds = sorted(list(self.orig_books.keys()))
        return [
            self.orig_books[ind].book_info.summary_text
            for ind in inds
        ]

    def export_summary_to_tsv(self, filename):
        summaries = self.get_all_summaries_inorder()
        
        with open(filename, 'w') as out_file:
            tsv_writer = csv.writer(out_file, delimiter='\t')
            tsv_writer.writerow(['Text'])
            for summary in summaries:
                tsv_writer.writerow([summary])

    def export_summary_to_txt(self, filename):
        summaries = self.get_all_summaries_inorder()
        
        with open(filename, 'w') as out_file:
            print('Text', file=out_file)
            for summary in summaries:
                print(summary, file=out_file)

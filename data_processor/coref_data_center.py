from dataclasses import dataclass
from typing import Dict, List

from .coref_utils import CorefBook, CorefCharacter
from .coref_result_reader import CorefResultReader

@dataclass
class CorefBookDataCenter(object):
    coref_books: Dict[int, CorefBook]

    @classmethod
    def build_from_file(cls, filename: str):
        reader = CorefResultReader.build_from_file(filename)
        return cls(reader.paragraphs)

    def __len__(self) -> int:
        return len(self.coref_books)

    def __getitem__(self, ind: int) -> CorefBook:
        return self.coref_books[ind]

    def indices(self) -> List[int]:
        return list(self.coref_books.keys())

    def validate(self):
        pass

@dataclass
class CorefCharDataCenter(object):
    coref_chars: Dict[int, CorefCharacter]

    @classmethod
    def build_from_file(cls, filename: str):
        reader = CorefResultReader.build_from_file(filename)
        return cls(reader.paragraphs)

    def __len__(self) -> int:
        return len(self.coref_chars)

    def __getitem__(self, ind: int) -> CorefBook:
        return self.coref_chars[ind]

    def indices(self) -> List[int]:
        return list(self.coref_chars.keys())

    def validate(self):
        pass

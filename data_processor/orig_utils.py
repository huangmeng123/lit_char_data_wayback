from dataclasses import dataclass, asdict
from typing import Tuple, Dict, List

OrigLitKey = Tuple[str, str]

@dataclass
class OrigLiteratureInfo:
    book_ind: int
    book_title: str
    source: str
    book_url: str
    author: str
    summary_url: str
    summary_text: str
    character_list_url: str

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def key(self) -> OrigLitKey:
        return (self.book_title.strip(), self.source.strip())


OrigCharKey = Tuple[str, str, str]

@dataclass
class OrigCharacterInfo:
    character_name: str
    book_title: str
    source: str
    character_list_url: str
    character_order: int
    description_url: str
    description_text: str
    analysis_url: str
    analysis_text: str

    def to_dict(self) -> dict:
        return asdict(self)
    
    @property
    def key(self) -> OrigCharKey:
        char_name = self.character_name
        char_name = char_name.replace('\n', ' ')
        char_name = char_name.replace('%', ' ')
        char_name = ' '.join(char_name.strip().split())
        return (
            self.book_title.strip(),
            self.source.strip(),
            char_name,
        )

    @property
    def lit_key(self) -> OrigLitKey:
        return (self.book_title.strip(), self.source.strip())



@dataclass
class OrigBook:
    book_info: OrigLiteratureInfo
    characters: Dict[str, OrigCharacterInfo]

    @staticmethod
    def split_summary(summary: str) -> List[str]:
        replacements: List[Tuple[str, str]] = [
            # honorific titles
            ('Mr.', 'Mr'),
            ('Ms.', 'Ms'),
            ('Mrs.', 'Mrs'),
            ('Mrs .', 'Mrs'),
            ('Sir.', 'Sir'),
            ('Dr.', 'Dr'),
            (' D.', ' D'),

            # manually corrected abbrv.
            ('D.C.', 'D.C'),
            ('D.H.', 'D.H'),
            ('A.D.', 'A.D'),
            ('B.D.', 'B.D'),
            ('Ph.D.', 'Ph.D'),
            ('D.A.', 'D.A'),
            ('I.D.', 'I.D'),
            ('P.D.', 'P.D'),
            ('J.D.', 'J.D'),

            # compound punctuations
            ('?', '?|'),
            ('!', '!|'),
            ('.', '.|'),
            ('|"', '"|'),
            ('| ', '|'),
        ]

        for old, new in replacements:
            summary = summary.replace(old, new)
        
        sents = summary.strip().split('|')
        sents = list(filter(lambda s: len(s) > 0, sents))
        return sents

    def to_dict(self) -> dict:
        return {
            'book_info': asdict(self.book_info),
            'characters': {
                char_name: asdict(char_info)
                for char_name, char_info in self.characters.items()
            },
        }

    @property
    def num_characters(self) -> int:
        return len(self.characters)

    def get_sentence_based_summary(self) -> List[str]:
        summary = self.book_info.summary_text
        return OrigBook.split_summary(summary)

    def validate(self):
        # check if summary is empty
        assert(self.book_info.summary_text is not None)
        assert(len(self.book_info.summary_text) > 0)

        # check if any character description is empty
        for char in self.characters.values():
            assert(char.description_text is not None)
            assert(len(char.description_text) > 0)

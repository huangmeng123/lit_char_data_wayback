from dataclasses import dataclass, asdict

@dataclass
class Literature:
    book_ind: int
    book_title: str
    source: str
    book_url: str
    author: str
    summary_url: str
    summary_text: str
    character_list_url: str

    def to_dict(self):
        return asdict(self)

@dataclass
class Character:
    character_name: str
    book_title: str
    source: str
    character_list_url: str
    character_order: int
    description_url: str
    description_text: str
    analysis_url: str
    analysis_text: str

    def to_dict(self):
        return asdict(self)

@dataclass
class OriginalBook:
    book_info: Literature
    characters: dict # name to character infos

    def to_dict(self):
        return {
            'book_info': asdict(self.book_info),
            'characters': {
                key: asdict(char_info)
                for key, char_info in self.characters.items()
            },
        }

@dataclass
class CorefBookSection:
    book_ind: int
    section_ind: int
    tokens: [str] # sentences
    token_to_sentence: [int] # sentence_map
    token_to_subtoken: [int] # subtoken_map
    references: [[[int]]] # predcted_clusters

    @classmethod
    def from_json(cls, data):
        b_ind, s_ind = map(int, data['doc_index'].split('-'))
        # ignored "doc_key"
        tokens = data['sentences'][0]
        # ignored "speakers"
        token_to_sentence = data['sentence_map']
        token_to_subtoken = data['subtoken_map']
        # ignored "clusters"
        references = data['predicted_clusters']
        # ignored "top_spans"
        # ignored "head_scores"

        return cls(
            book_ind=b_ind,
            section_ind=s_ind,
            tokens=tokens,
            token_to_sentence=token_to_sentence,
            token_to_subtoken=token_to_subtoken,
            references=references,
        )

@dataclass
class CorefBook:
    book_ind: int
    tokens: [str]
    token_to_sentence: [int]
    num_sentences: int
    token_to_subtoken: [int]
    num_subtokens: int
    references: [[[int]]]
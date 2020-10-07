import json
import nltk

from database import DatabaseConnection
from data_schema import Literature, Character
from data_schema import OriginalBook

# download nltk data for parsing sentences
nltk.download('punkt')

class DataCenter(object):
    @staticmethod
    def get_lit_key(lit: Literature):
        return (lit.book_title, lit.source)

    @staticmethod
    def get_char_key(char: Character):
        return (char.character_name, char.book_title, char.source)

    def __init__(self, literatures=None, characters=None):
        db = DatabaseConnection()
        
        if literatures is None:
            literatures = db.read_literature_data()
        else:
            literatures = [Literature(**lit) for lit in literatures]
        self.literatures = {}
        for literature in literatures:
            key = DataCenter.get_lit_key(literature)
            self.literatures[key] = literature
        
        if characters is None:
            characters = db.read_character_data()
        else:
            characters = [Character(**char) for char in characters]
        self.characters = {}
        for character in characters:
            key = DataCenter.get_char_key(character)
            self.characters[key] = character
            
        db.close()

        self.merged_original_books = {}
        for lit in self.literatures.values():
            self.merged_original_books[lit.book_ind] = OriginalBook(
                book_info=lit,
                characters={},
            )
        for char in self.characters.values():
            lit = self.literatures.get((char.book_title, char.source), None)
            if lit is None: continue
            
            book = self.merged_original_books[lit.book_ind]
            book.characters[char.character_name] = char

    def export_to_file(self, filename):
        data = {
            'literatures': [lit.to_dict() for lit in self.literatures.values()],
            'characters': [char.to_dict() for char in self.characters.values()],
        }
        with open(filename, 'w') as outfile:
            json.dump(data, outfile)

    @classmethod
    def build_from_file(cls, filename):
        with open(filename) as json_file:
            data = json.load(json_file)
        return cls(data['literatures'], data['characters'])

    def get_sentence_based_summary(self, ind):
        summary = self.merged_original_books[ind].book_info.summary_text
        return nltk.tokenize.sent_tokenize(summary)

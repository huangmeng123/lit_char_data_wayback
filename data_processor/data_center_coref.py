import json

from data_schema import Literature, Character
from data_schema import CorefBookSection, CorefBook

IGNORED_TOKENS = ['[SPL]', '[SEP]', '[CLS]']

class CorefDataCenter(object):
    def __init__(self, sections: [CorefBookSection]):
        raw_coref_books = {}
        for section in sections:
            b_ind, s_ind = section.book_ind, section.section_ind
            cluster = raw_coref_books.get(b_ind, {})
            cluster[s_ind] = section
            raw_coref_books[b_ind] = cluster

        self.merged_coref_books = {}
        for b_ind, cluster in raw_coref_books.items():
            book = CorefBook(
                book_ind=b_ind,
                tokens=[],
                token_to_sentence=[],
                num_sentences=0,
                token_to_subtoken=[],
                num_subtokens=0,
                references=[],
            )

            num_tokens = 0
            s_inds = list(cluster.keys())
            s_inds.sort()
            for s_ind in s_inds:
                section = cluster[s_ind]
                
                book.tokens.extend(section.tokens)

                book.token_to_sentence.extend(
                    [i+book.num_sentences for i in section.token_to_sentence],
                )
                book.num_sentences = max(book.token_to_sentence) + 1

                book.token_to_subtoken.extend(
                    [i+book.num_subtokens for i in section.token_to_subtoken],
                )
                book.num_subtokens = max(book.token_to_subtoken) + 1

                book.references.extend([
                    [[a+num_tokens, b+num_tokens] for a, b in ref]
                    for ref in section.references
                ])

                num_tokens = len(book.tokens)
            
            
            assert(len(book.token_to_sentence) == num_tokens)
            assert(len(book.token_to_subtoken) == num_tokens)

            self.merged_coref_books[b_ind] = book

    @classmethod
    def build_from_raw_file(cls, filename):
        sections: [CorefBookSection] = []
        with open(filename) as json_file:
            for line in json_file.readlines():
                section = CorefBookSection.from_json(json.loads(line))
                sections.append(section)
        return cls(sections)

    def get_token_based_summary(self, key):
        book: CorefBook = self.merged_coref_books[key]
        tokens = book.tokens
        token_to_sentence = book.token_to_sentence
        num_sentences = book.num_sentences
        num_tokens = len(tokens)
        
        breaks = []
        for i in range(num_sentences):
            breaks.append(token_to_sentence.index(i))
        breaks.append(num_tokens)
        sentences = [tokens[i:j] for i, j in zip(breaks[:-1], breaks[1:])]

        merged_sentences = []
        for sentence in sentences:
            merged_sentence = []
            buf = None
            for token in sentence:
                if token.startswith('##'):
                    buf += token[2:]
                else:
                    if buf is not None:
                        merged_sentence.append(buf)
                    buf = token
            merged_sentence.append(buf)
            merged_sentences.append(merged_sentence)
        return merged_sentences

    def get_merged_token_based_summary(self, key):
        summary = self.get_token_based_summary(key)
        merged_coref_summary = []
        for i, tokens in enumerate(summary):
            sentence = [(token, i) for token in tokens if token not in IGNORED_TOKENS]
            merged_coref_summary.extend(sentence)
        return merged_coref_summary

    def get_readable_summary(self, key):
        summary_tokens = self.get_merged_token_based_summary(key)
        sentences = [
            [] for _ in range(self.merged_coref_books[key].num_sentences)
        ]
        for token, i in summary_tokens:
            sentences[i].append(token)
        return '\n'.join([' '.join(sentence) for sentence in sentences])

    def get_token_based_references(self, key):
        book: CorefBook = self.merged_coref_books[key]

        tokens = book.tokens
        references = book.references
        token_to_sentence = book.token_to_sentence

        reference_tokens = [
            [[tokens[a:b+1], token_to_sentence[a]] for a, b in ref]
            for ref in references
        ]
        new_references = []
        for mentions in reference_tokens:
            new_mentions = []
            for mention_tokens, s_i in mentions:
                buf = None
                mention = []
                for token in mention_tokens:
                    if token in IGNORED_TOKENS:
                        continue
                    if token.startswith('##'):
                        if buf is None:
                            buf = token
                        else:
                            buf += token[2:]
                    else:
                        if buf is not None:
                            mention.append(buf)
                        buf = token
                mention.append(buf)
                new_mentions.append((tuple(mention), s_i))
            new_references.append(new_mentions)
        return new_references
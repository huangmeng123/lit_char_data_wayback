import json
import csv
import string

import time, sys
from datetime import datetime

import numpy as np
from numpy.linalg import norm

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

IGNORED_TOKENS = ['[SPL]', '[SEP]', '[CLS]']

ORIGINAL_DATA_FILENAME = 'data/orig_data_ordered.json'
SUMMARY_REF_FILENAME = 'data/orig_data_summary.json'
# COREF_OUTPUT_FILENAME = 'short-desc-summeries-spanbert-base-400.out'
COREF_OUTPUT_FILENAME = 'data/coref-trunc-orig_data_summary.json'
OUTPUT_FILENAME = 'data/advanced_data_ordered.json'

lemmatizer = WordNetLemmatizer()

def calc_similarity(s1, s2, lemma_func=lambda w: w):
    s1_tokens = [lemma_func(w) for w in word_tokenize(s1)]
    s2_tokens = [lemma_func(w) for w in word_tokenize(s2)]
    sw = stopwords.words('english')

    s1_set = {w for w in s1_tokens if not w in sw}
    s2_set = {w for w in s2_tokens if not w in sw}
    if len(s1_set) == 0 or len(s2_set) == 0:
        return 0.0

    rvector = list(s1_set | s2_set)
    l1 = np.zeros(len(rvector))
    l2 = np.zeros(len(rvector))
    for i, w in enumerate(rvector):
        if w in s1_set: l1[i] = 1
        if w in s2_set: l2[i] = 1
    
    cosine = np.dot(l1, l2) / (norm(l1) * norm(l2))

    return cosine

def calc_right_similarity(s1, s2, lemma_func=lambda w: w):
    s1_tokens = [lemma_func(w) for w in word_tokenize(s1)]
    s2_tokens = [lemma_func(w) for w in word_tokenize(s2)]
    sw = stopwords.words('english')

    s1_set = {w for w in s1_tokens if not w in sw}
    s2_set = {w for w in s2_tokens if not w in sw}
    if len(s1_set) == 0 or len(s2_set) == 0:
        return 0.0

    rvector = list(s2_set)
    l1 = np.zeros(len(rvector))
    l2 = np.ones(len(rvector))
    for i, w in enumerate(rvector):
        if w in s1_set: l1[i] = 1
    
    if norm(l1) == 0.0:
        return 0.0

    cosine = np.dot(l1, l2) / (norm(l1) * norm(l2))

    return cosine

def calc_shared_ratio(s1, s2, lemma_func=lambda w: w):
    s1_tokens = [lemma_func(w) for w in word_tokenize(s1)]
    s2_tokens = [lemma_func(w) for w in word_tokenize(s2)]
    sw = stopwords.words('english')

    s1_set = {w for w in s1_tokens if not w in sw}
    s2_set = {w for w in s2_tokens if not w in sw}
    if len(s1_set) == 0 or len(s2_set) == 0:
        return 0.0

    return len(s1_set & s2_set) / len(s2_set)

class CorefBookData(object):
    @staticmethod
    def convert_inds_to_tokens(tokens, start, end):
        return tokens[start:end+1]

    def __init__(self, filename):
        self.raw_coref_books = {}
        with open(filename) as f:
            for line in f.readlines():
                section = json.loads(line)

                b_ind, s_ind = section['doc_index'].split('-')
                # ignored "doc_key"
                tokens = section['sentences'][0]
                # ignored "speakers"
                token_to_sentence = section['sentence_map']
                token_to_subtoken = section['subtoken_map']
                # ignored "clusters"
                references = section['predicted_clusters']
                # ignored "top_spans"
                # ignored "head_scores"

                sections = self.raw_coref_books.get(int(b_ind), {})
                sections[int(s_ind)] = {
                    'tokens': tokens,
                    'token_to_sentence': token_to_sentence,
                    'token_to_subtoken': token_to_subtoken,
                    'references': references,
                }
                self.raw_coref_books[int(b_ind)] = sections

        self.merged_coref_books = {}
        for b_ind, sections in self.raw_coref_books.items():
            tokens = []
            token_to_sentence = []
            token_to_subtoken = []
            references = []

            num_tokens, num_sentences, num_subtokens = 0, 0, 0
            s_inds = list(sections.keys())
            s_inds.sort()
            for s_ind in s_inds:
                section = sections[s_ind]
                
                tokens.extend(section['tokens'])
                
                token_to_sentence.extend([i+num_sentences for i in section['token_to_sentence']])
                num_sentences = max(token_to_sentence) + 1
                
                token_to_subtoken.extend([i+num_subtokens for i in section['token_to_subtoken']])
                num_subtokens = max(token_to_subtoken) + 1

                references.extend(
                    [[[a+num_tokens, b+num_tokens] for a, b in ref] for ref in section['references']],
                )
                num_tokens = len(tokens)

            assert(len(tokens) == len(token_to_sentence) == len(token_to_subtoken))

            self.merged_coref_books[b_ind] = {
                'tokens': tokens,
                'token_to_sentence': token_to_sentence,
                'num_sentences': num_sentences,
                'token_to_subtoken': token_to_subtoken,
                'num_subtokens': num_subtokens,
                'references': references,
            }

    def __getitem__(self, key):
        return self.merged_coref_books[key]

    def get_book_inds(self):
        keys = list(self.raw_coref_books.keys())
        keys.sort()
        return keys

    def get_token_based_summary(self, key):
        book = self.merged_coref_books[key]
        tokens = book['tokens']
        token_to_sentence = book['token_to_sentence']
        num_sentences = book['num_sentences']
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

    def get_token_based_references(self, key):
        book = self.merged_coref_books[key]

        tokens = book['tokens']
        references = book['references']
        token_to_sentence = book['token_to_sentence']

        reference_tokens = [[[tokens[a:b+1], token_to_sentence[a]] for a, b in ref] for ref in references]
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
                new_mentions.append([mention, s_i])
            new_references.append(new_mentions)
        return new_references



class OriginalBookData(object):
    def __init__(self, filename, ref_filename):
        books = {}
        with open(filename) as f:
            data = json.load(f)
            for d in data:
                title = d['book_title']
                source = d['source']
                summary = d['summary']
                character_name = d['character_name']
                character_order = d['character_order']
                character_description = d['character_description']

                book = books.get((title, source), {
                    'book_title': title,
                    'source': source,
                    'summary': summary,
                    'characters': {}
                })
                book['characters'][character_name] = {
                    'character_order': character_order,
                    'character_description': character_description,
                }
                books[(title, source)] = book

        with open(ref_filename) as f:
            book_order = json.load(f)

        self.raw_orig_books = {
            i: books[(o['book_title'], o['source'])]
            for i, o in enumerate(book_order) if (o['book_title'], o['source']) in books
        }

    def __getitem__(self, key):
        return self.raw_orig_books[key]

    def get_book_inds(self):
        keys = list(self.raw_orig_books.keys())
        keys.sort()
        return keys

    def get_token_based_summary(self, key):
        book = self.raw_orig_books[key]
        summary = book['summary']
        new_summary = ''
        for c in summary:
            if not c.isalnum():
                new_summary += f' {c} '
            else:
                new_summary += c
        return list(filter(lambda w: len(w) > 0, new_summary.split()))

    def get_character_names(self, key):
        book = self.raw_orig_books[key]
        characters = list(book['characters'].keys())
        characters.sort(key=lambda c: book['characters'][c]['character_order'])
        return characters

    def get_character_data(self, key):
        book = self.raw_orig_books[key]
        return book['characters']


class MergedBookData(object):
    def __init__(self):
        pass

    def import_from_data(self, coref_book_data, orig_book_data):
        coref_inds = coref_book_data.get_book_inds()
        orig_inds = orig_book_data.get_book_inds()

        inds = list(set(coref_inds) & set(orig_inds))
        inds.sort()
        self.books = {}

        thresholds = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        counts = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        
        for b_ind in inds:
            try:
                print(f'book index - {b_ind}')
                # merge summary
                print('merging summary...')
                coref_summary_tokens = coref_book_data.get_merged_token_based_summary(b_ind)
                orig_summary_tokens = orig_book_data.get_token_based_summary(b_ind)
                merged_summary_tokens = []
                i = 0
                for j in range(len(orig_summary_tokens)):
                    while i < len(coref_summary_tokens) and coref_summary_tokens[i][0] != orig_summary_tokens[j]:
                        i += 1
                    merged_summary_tokens.append(coref_summary_tokens[i])
                    i += 1

                merged_tokens = [token for token, _ in merged_summary_tokens]
                token_to_sentence = [i for _, i in merged_summary_tokens]
                num_tokens = len(merged_tokens)
                num_sentences = max(token_to_sentence) + 1

                breaks = []
                for i in range(num_sentences):
                    breaks.append(token_to_sentence.index(i))
                breaks.append(num_tokens)
                summary_sentences = [merged_tokens[i:j] for i, j in zip(breaks[:-1], breaks[1:])]

                # correlate references
                print('correlating references...')
                references = coref_book_data.get_token_based_references(b_ind)
                character_names = orig_book_data.get_character_names(b_ind)

                character_summaries = {cname: set() for cname in character_names}
                for mentions in references:
                    sentence_inds = set([s_i for _, s_i in mentions])
                    for cname in character_names:
                        for mention_tokens, _ in mentions:
                            mention = ' '.join(mention_tokens)
                            sim = calc_similarity(mention, cname)
                            if sim > 0.3:
                                character_summaries[cname] |= sentence_inds
                                break
                
                character_data = orig_book_data.get_character_data(b_ind)
                new_character_data = {}
                for cname, sentence_inds in character_summaries.items():
                    new_character_data[cname] = {key:val for key, val in character_data[cname].items()}
                    sentence_inds = list(sentence_inds)
                    sentence_inds.sort()
                    new_character_data[cname]['summary'] = [summary_sentences[i] for i in sentence_inds]

                # analyze description
                print('analyzing character description...')
                summary = ' '.join([' '.join(sentence) for sentence in summary_sentences])
                for cname, data in character_data.items():
                    description = data['character_description']
                    sim = calc_shared_ratio(summary, description, lemmatizer.lemmatize)
                    for i in range(len(thresholds)):
                        if sim > thresholds[i]:
                            counts[i] += 1
                    print(f'\t{cname} - {sim}')
                    new_character_data[cname]['similarity'] = sim

                print()

                self.books[b_ind] = {
                    'summary': summary_sentences,
                    'characters': new_character_data,

                    'coref_data': coref_book_data[b_ind],
                    'original_data': orig_book_data[b_ind],
                }
            except Exception as e:
                print(e)

        for i in range(len(thresholds)):
            print(f'threshold: {thresholds[i]}, count: {counts[i]}, perc: {(100 * counts[i] / counts[0]):.2f} %')

    def __getitem__(self, key):
        return self.books[key]

    def get_summary(self, key):
        return self.books[key]['summary']

    def get_character_data(self, key):
        return self.books[key]['characters']

    def export_to_file(self, filename):
        with open(filename, 'w', encoding='utf-8') as out_f:
            json.dump(self.books, out_f)

    def import_from_file(self, filename):
        with open(filename, encoding='utf-8') as in_f:
            self.books = {int(key):val for key, val in json.load(in_f).items()}

    def convert_to_character_based_data(self):
        character_data = []
        for b_ind, book in self.books.items():
            for cname, cdata in book['characters'].items():
                character_data.append({
                    'bindex': b_ind,
                    'book_title': book['original_data']['book_title'],
                    'source': book['original_data']['source'],
                    'summary': ' '.join([' '.join(sentence) for sentence in book['summary']]),
                    'character_name': cname,
                    'character_order': cdata['character_order'],
                    'character_summary': ' '.join([' '.join(sentence) for sentence in cdata['summary']]),
                    'character_description': cdata['character_description'],
                    'similarity_score': cdata['similarity'],
                })
        return character_data


def main():
    coref_book_data = CorefBookData(
        filename=COREF_OUTPUT_FILENAME,
    )
    orig_book_data = OriginalBookData(
        filename=ORIGINAL_DATA_FILENAME,
        ref_filename=SUMMARY_REF_FILENAME,
    )

    merged_book_data = MergedBookData()
    merged_book_data.import_from_data(coref_book_data, orig_book_data)
    merged_book_data.export_to_file(f'save_points/merged_book_data_{datetime.timestamp(datetime.now())}.json')

    # merged_book_data.import_from_file('save_points/merged_book_data_1588640502.0843.json')
    data = merged_book_data.convert_to_character_based_data()
    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as out_f:
        json.dump(data, out_f)


def test():
    coref_book_data = CorefBookData(
        filename=COREF_OUTPUT_FILENAME,
    )
    orig_book_data = OriginalBookData(
        filename=ORIGINAL_DATA_FILENAME,
        ref_filename=SUMMARY_REF_FILENAME,
    )

    coref_inds = coref_book_data.get_book_inds()
    orig_inds = orig_book_data.get_book_inds()

    inds = list(set(coref_inds) & set(orig_inds))
    inds.sort()
    for b_ind in inds:
        coref_summary_tokens = coref_book_data.get_merged_token_based_summary(b_ind)
        orig_summary_tokens = orig_book_data.get_token_based_summary(b_ind)
        merged_summary_tokens = []
        i = 0
        for j in range(len(orig_summary_tokens)):
            while i < len(coref_summary_tokens) and coref_summary_tokens[i][0] != orig_summary_tokens[j]:
                i += 1
            merged_summary_tokens.append(coref_summary_tokens[i])
            i += 1

if __name__ == '__main__':
    main()
    # test()
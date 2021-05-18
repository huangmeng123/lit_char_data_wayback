from os import remove
from typing import Any, List, Dict, TextIO, Optional, Callable, Tuple

import sys
import logging
import re
import json
import nltk
from dataclasses import dataclass

from .orig_data_center import OrigBookDataCenter
from .coref_data_center import CorefBookDataCenter, CorefCharDataCenter
from .data_utils import ThresholdCounter, MergedBook, calc_rouge_L, tokenize
from .data_utils import FullCharacterInfo, ExtendedCharacterInfo

logging.basicConfig(
    filename='main.log',
    level=logging.DEBUG,
)

@dataclass
class BookDataTransformer(object):
    merged_books: Dict[int, MergedBook]

    @classmethod
    def build_from_data_center(
        cls,
        orig: OrigBookDataCenter,
        coref: CorefBookDataCenter,
    ):
        orig_inds = set(orig.indices())
        coref_inds = set(coref.indices())
        inds = sorted(list(coref_inds & orig_inds))

        merged_books: Dict[int, MergedBook] = {}
        for ind in inds:
            merged_books[ind] = MergedBook(
                orig_info=orig[ind],
                coref_info=coref[ind],
            )
        
        return cls(merged_books)

    def __getitem__(self, ind: int) -> MergedBook:
        return self.merged_books[ind]

    def __manual_match_summary(self, ind: int):
        orig_summary = self[ind].orig_info.get_sentence_based_summary()
        coref_summary = self[ind].coref_info.get_sentence_based_summary()

        l1 = len(orig_summary)
        l2 = len(coref_summary)
        if l1 != l2:
            print(f'{l1} vs {l2}')
            offset = 0
            j = 0
            auto_skip = False
            while 0 <= j < l2 or 0 <= j+offset < l1:
                orig_sent = (
                    orig_summary[j+offset] if 0 <= j+offset < l1
                    else ''
                )
                coref_sent = (
                    coref_summary[j] if 0 <= j < l2
                    else ''
                )
                print(f'Book {ind}')
                print(f'[{j+offset+1} / {l1}] - {orig_sent}')
                print()
                print(f'[{j+1} / {l2}] - {coref_sent}')
                print('-----------------------------------------------------')
                
                tokenizer = nltk.RegexpTokenizer(r"\w+")
                orig_tokens = tokenizer.tokenize(orig_sent)
                coref_tokens = tokenizer.tokenize(coref_sent)
                coref_tokens = list(filter(
                    lambda w: w not in ['CLS', 'SEP', 'SPL'],
                    coref_tokens,
                ))
                if auto_skip:
                    if len(orig_tokens) == len(coref_tokens):
                        j += 1
                        continue
                    else:
                        auto_skip = False
                
                a = input()
                if a == 'n': break
                elif a == 'd':
                    offset += 1
                    j -= 1
                elif a == 'a': offset -= 1
                elif a == 's': j -= 2
                elif a == 'f': auto_skip = True
                j += 1
        print('-----------------------------------------------------')

    def __check_num_sentence(self, ind: int):
        orig_summary = self[ind].orig_info.get_sentence_based_summary()
        coref_summary = self[ind].coref_info.get_sentence_based_summary()
        assert(len(coref_summary) == len(orig_summary))

    def indices(self) -> List[int]:
        return sorted(list(self.merged_books.keys()))

    def validate(self):
        for ind in self.merged_books.keys():
            self.__check_num_sentence(ind)
            # self.__manual_match_summary(ind)

    def print_similarity_stats(self, out_file: Optional[TextIO]=None):
        ref_char_counter = ThresholdCounter()
        summ_desc_counter = ThresholdCounter()
        inds = self.indices()
        l = len(inds)
        for i, ind in enumerate(inds):
            print(f'\r[Similarity] Processing {i+1} / {l} book ...', end='\r')
            book = self[ind]
            
            ref_char_similarity = book.get_ref_char_similarity()
            for score in ref_char_similarity.values():
                ref_char_counter.add(score)

            summ_desc_similarity = book.get_summ_desc_similarity()
            for score in summ_desc_similarity.values():
                summ_desc_counter.add(score)

        print('Reference v.s. Character Name', file=out_file)
        ref_char_counter.print(out_file)
        print(file=out_file)

        print('Summary v.s. Character Description', file=out_file)
        summ_desc_counter.print(out_file)
        print(file=out_file)

    def print_matchness_stats(self, out_file: Optional[TextIO]=None):
        summ_char_counters = {
            'rouge-1': ThresholdCounter(),
            'rouge-2': ThresholdCounter(),
            'rouge-l': ThresholdCounter(),
        }
        summ_desc_counters = {
            'rouge-1': ThresholdCounter(),
            'rouge-2': ThresholdCounter(),
            'rouge-l': ThresholdCounter(),
        }

        inds = self.indices()
        l = len(inds)
        for i, ind in enumerate(inds):
            print(f'[Matchness] Processing {i+1} / {l} book ...', end='\r')
            book = self[ind]
            
            summ_char_matchness = book.get_summ_char_matchness()
            for scores in summ_char_matchness.values():
                for key, score in scores.items():
                    summ_char_counters[key].add(score)

            summ_desc_matchness = book.get_summ_desc_matchness()
            for scores in summ_desc_matchness.values():
                for key, score in scores.items():
                    summ_desc_counters[key].add(score)

        for key, counter in summ_char_counters.items():
            print(f'Summary v.s. Character Name ({key})', file=out_file)
            counter.print(out_file)
            print(file=out_file)

        for key, counter in summ_desc_counters.items():
            print(
                f'Summary v.s. Character Description ({key})',
                file=out_file,
            )
            counter.print(out_file)
            print(file=out_file)

    def generate_full_character_dataset(
        self,
        filter_func: Callable[[dict], bool]=lambda x: True,
    ):
        dataset: List[dict] = []

        inds = self.indices()
        l = len(inds)
        for i, ind in enumerate(inds):
            print(f'[Dataset] Processing {i+1} / {l} ...', end='\r')
            book = self[ind]
            
            # ref_char_similarity = book.get_ref_char_similarity()
            summ_char_matchness = book.get_summ_char_matchness()

            # summ_desc_similarity = book.get_summ_desc_similarity()
            summ_desc_matchness = book.get_summ_desc_matchness()

            for char_name in book.orig_info.characters.keys():
                char_info = book.orig_info.characters[char_name]

                # rc_sim = ref_char_similarity[char_name]
                sc_match = summ_char_matchness[char_name]
                # sd_sim = summ_desc_similarity[char_name]
                sd_match = summ_desc_matchness[char_name]
                
                full_char_info = FullCharacterInfo.from_dict({
                    'character_name': char_name,
                    'book_title': book.orig_info.book_info.book_title,
                    'source': book.orig_info.book_info.source,
                    'summary': book.orig_info.book_info.summary_text,
                    'description': char_info.description_text,
                    'character_order': char_info.character_order,
                    # 'sim_score': sd_sim,
                    'rouge-l': sd_match['rouge-l'],
                    
                    'score_details': {
                        'name': {
                            # 'sim': rc_sim,
                            # 'rouge-1': sc_match['rouge-1'],
                            # 'rouge-2': sc_match['rouge-2'],
                            'rouge-l': sc_match['rouge-l'],
                        },
                        'description': {
                            # 'sim': sd_sim,
                            # 'rouge-1': sd_match['rouge-1'],
                            # 'rouge-2': sd_match['rouge-2'],
                            'rouge-l': sd_match['rouge-l'],
                        },
                    },
                })
                dataset.append(full_char_info.to_dict())
        
        return list(filter(filter_func, dataset))

    def generate_truncated_summary_character_dataset(
        self,
        filter_func: Callable[[dict], bool]=lambda x: True,
    ):
        dataset: List[dict] = []

        inds = self.indices()
        l = len(inds)
        for i, ind in enumerate(inds):
            print(f'[Trunc Dataset] Processing {i+1} / {l} ...', end='\r')
            book = self[ind]
            trunc_summaries = book.get_coref_truncated_summary()

            for char_name in book.orig_info.characters.keys():
                char_info = book.orig_info.characters[char_name]
                trunc_char_info = {
                    'character_name': char_name,
                    'book_title': book.orig_info.book_info.book_title,
                    'source': book.orig_info.book_info.source,
                    'summary': book.orig_info.book_info.summary_text,
                    'coref_truncated_summary': trunc_summaries[char_name],
                    'description': char_info.description_text,
                    'character_order': char_info.character_order,
                }
                dataset.append(trunc_char_info)
        
        return list(filter(filter_func, dataset))

    def get_gender_count(
        self, target_chars: Dict[Tuple[str, str], List[str]],
    ) -> Dict[Tuple[str, str], Dict[str, Tuple[int, int, int]]]:
        inds = self.indices()
        l = len(inds)
        total_gender_count: Dict[Tuple[str, str], Dict[str, Tuple[int, int, int]]] = {}
        for i, ind in enumerate(inds):
            print(f'[Gender Bias] Processing {i+1} / {l} ...', end='\r')
            book = self[ind]
            book_title = book.orig_info.book_info.book_title
            source = book.orig_info.book_info.source
            key = (book_title, source)
            if key not in target_chars: continue
            gender_count = book.get_summ_gender_count(target_chars[key])
            total_gender_count[key] = gender_count
        return total_gender_count


def print_score_stats_from_dataset_file(filename: str):
    with open(filename) as in_file:
        data: List[Dict[str, Any]] = json.load(in_file)
    
    # name_counters: Dict[str, ThresholdCounter] = {}
    # desc_counters: Dict[str, ThresholdCounter] = {}
    # for key in ['sim', 'rouge-1', 'rouge-2', 'rouge-l']:
    #     name_counters[key] = ThresholdCounter()
    #     desc_counters[key] = ThresholdCounter()
    # for d in data:
    #     for key, score in d['score_details']['name'].items():
    #         name_counters[key].add(score)
    #     for key, score in d['score_details']['description'].items():
    #         desc_counters[key].add(score)
    
    # for key in ['sim', 'rouge-1', 'rouge-2', 'rouge-l']:
    #     print(f'Summary v.s. Character Name ({key})')
    #     name_counters[key].print()
    #     print()
    #     print(f'Summary v.s. Character Description ({key})')
    #     desc_counters[key].print()
    #     print()

    # counter = ThresholdCounter([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.8, 1, 1.2, 3, 6])
    counter = ThresholdCounter()
    for d in data:
        if (d['score_details']['name']['rouge-l'] < 0.6
            and d['character_order'] >= 3):
            continue
        score = d['score_details']['description']['sim']
        counter.add(score)
    
    counter.print()

    # name_rouge_l: List[float] = [
    #     d['score_details']['name']['rouge-l'] for d in data
    # ]
    # desc_rouge_l: List[float] = [
    #     d['score_details']['description']['rouge-l'] for d in data
    #     if d['score_details']['name']['rouge-l'] >= 0.6
    # ]

    # for q in range(0, 11):
    #     qq = q / 10
    #     # name_val = np.quantile(name_rouge_l, qq)
    #     desc_val = np.quantile(desc_rouge_l, qq)
    #     print(f'{10*q}th quantile')
    #     # print(f'\tname: {name_val:.4f}')
    #     print(f'\tdescription: {desc_val:.4f}\n')
    # print(f'mean')
    # # print(f'\tname: {np.mean(name_rouge_l):.4f}')
    # print(f'\tdescription: {np.mean(desc_rouge_l):.4f}')

@dataclass
class CharDataTransformer(object):
    char_infos: Dict[int, FullCharacterInfo]
    coref_char: CorefCharDataCenter

    @classmethod
    def build_from_file(
        cls,
        full_char_filename: str,
        coref_desc_filename: str,
    ):
        with open(full_char_filename) as in_file:
            infos = json.load(in_file)
        data = CorefCharDataCenter.build_from_file(coref_desc_filename)
        return cls(
            char_infos={
                i: FullCharacterInfo.from_dict(info)
                for i, info in enumerate(infos)
            },
            coref_char=data,
        )

    def validate(self):
        print('Validating data...')
        assert(len(self.char_infos) == len(self.coref_char))

        for i in self.coref_char.indices():
            coref_tokens, _ = self.coref_char[i].get_tokens()
            _, valid_tokens, _ = (
                CharDataTransformer.
                extract_orig_description_tokens(
                    self.char_infos[i].description,
                )
            )
            cond = (len(valid_tokens) == len(coref_tokens))
            found = False
            for t1, t2 in zip(coref_tokens, valid_tokens):
                if t1 != t2:
                    found = True
                    break
            assert(cond or not found)


    @staticmethod
    def extract_orig_description_tokens(
        desc: str,
    ) -> Tuple[List[str], List[str], List[int]]:
        desc = desc.replace('"', '""')
        if desc.endswith('""'):
            desc = desc[:-2]
        if desc.startswith('""'):
            desc = desc[2:]
        tokens = re.split(r'\b|\s+', desc)
        alphanums = r'a-zA-ZÀ-ÿō←œ©\d'
        word = fr'[{alphanums}]+'
        punc = fr'[^{alphanums}\s]'
        spaces = r'\s+'
        all = r'(' + r'|'.join([word, punc, spaces]) + r')'
        tokens = re.findall(all, desc)

        ignores = ['\x93', '\x94']
        tokens = list(filter(lambda w: w not in ignores, tokens))

        valid_tokens: List[str] = []
        mapping: List[int] = []
        for i, token in enumerate(tokens):
            if not re.match(r'\s+', token):
                valid_tokens.append(token)
                mapping.append(i)
            
        return tokens, valid_tokens, mapping

    @staticmethod
    def get_match_score(name: str, mention: str) -> float:
        name_tokens = tokenize(name, use_lemmatizer=True)
        mention_tokens = tokenize(mention, use_lemmatizer=True)
        return calc_rouge_L(mention_tokens, name_tokens)['right_score']

    def get_masked_description(self, i) -> str:
        book_title = self.char_infos[i].book_title
        source = self.char_infos[i].source
        char_name = self.char_infos[i].character_name
        _, coref_mapping = self.coref_char[i].get_tokens()

        # clean description
        description = self.char_infos[i].description
        description = description.replace('\u2013', '-')
        description = description.replace('\u2019', "'")

        raw_tokens, _, mapping = (
            CharDataTransformer.extract_orig_description_tokens(
                description,
            )
        )
        name_tokens, _, _ = (
            CharDataTransformer.extract_orig_description_tokens(
                char_name,
            )
        )
        nl = len(name_tokens)
        masked_tokens = raw_tokens[:]

        for ref in self.coref_char[i].references:
            max_score = 0.0
            for (a, b) in ref:
                a, b = coref_mapping[a], coref_mapping[b]
                if a is None or b is None: continue

                a, b = mapping[a], mapping[b]
                mention = ''.join(raw_tokens[a:b+1])
                score = CharDataTransformer.get_match_score(
                    char_name,
                    mention,
                )
                max_score = max(max_score, score)
            
            if max_score < 0.5: continue
            for (a, b) in ref:
                a, b = coref_mapping[a], coref_mapping[b]
                if a is None or b is None: continue

                a, b = mapping[a], mapping[b]
                mention = ''.join(raw_tokens[a:b+1])
                if self.char_infos[i].source == 'cliffnotes' and a < nl <= b:
                    continue
                
                if mention.find(char_name) != -1 and mention != char_name:
                    continue

                # print(raw_tokens[b-1], raw_tokens[b])
                if masked_tokens[a] != '':
                    masked_tokens[a] = '[MASK]'
                bb = b
                if b != a and raw_tokens[b-1] in ["'", "’"] and raw_tokens[b] == 's':
                    bb = b - 2
                for j in range(a+1, bb+1):
                    masked_tokens[j] = ''
        
        masked_desc = ''.join(masked_tokens)
        masked_desc = masked_desc.replace(char_name, '[MASK]')
        names = char_name.strip().split()
        if len(names) == 2:
            masked_desc = masked_desc.replace(names[0], '[MASK]')

        return masked_desc.strip()

    def post_static_clean_mask_desc(self, extended_char_info: ExtendedCharacterInfo):
        book_title = extended_char_info.book_title
        source = extended_char_info.source
        char_name = extended_char_info.character_name
        masked_desc = extended_char_info.masked_description
        
        # [book_title], [source], [char_name] 
        removes: Dict[Tuple[str, str, str], str] = {
            ('Brideshead Revisited', 'shmoop', 'Celia Mulcaster'):
            ''' Read about this ""Foil"" in Shmoop's '''
            '''""Character Role ID"" and you'll see what we're '''
            '''talking about.''',

            ('Catching Fire', 'shmoop', 'Gale Hawthorne'):
            ' Read our character analyses of [MASK] in The Hunger '
            'Games and Mockingjay.',
            
            ('Oedipus at Colonus', 'shmoop', 'Ismene'):
            ' Read more about [MASK] here.',

            ('The Brothers Karamazov', 'shmoop', 'Dmitri (Mitya) Karamazov'):
            ' (Read more about Schiller here.)',

            ('The Man in the Iron Mask', 'shmoop', "D'Artagnan"):
            ' Read on for more.',

            ('The Merchant of Venice', 'shmoop', 'Nerissa'):
            ' Read all about it in our analysis of Graziano.',

            ('Treasure Island', 'shmoop', 'Long John Silver'):
            ' (Read more about Henley here.)',

            ('Oedipus at Colonus', 'shmoop', 'Creon'):
            'Read up on Big Bad Uncle [MASK] in Oedipus the King and '
            'Antigone. ',

            ('The Circle', 'shmoop', 'Ty Gospodinov'):
            ' Read with caution.',
        }
        key = (book_title, source, char_name)
        if key in removes:
            r = removes[key]
            masked_desc = masked_desc.replace(r, '')

        while masked_desc.endswith('Read an'):
            masked_desc = masked_desc[:-7].strip()

        modified = True
        while modified:
            modified = False
            for prefix in ['[MASK] ', '[MASK]; ', '[MASK]. ']:
                if masked_desc.startswith(prefix) and (
                    masked_desc[len(prefix)].isupper() or
                    masked_desc[len(prefix):len(prefix)+6] == '[MASK]'
                ):
                    masked_desc = masked_desc[len(prefix):]
                    modified = True

        masked_desc = masked_desc.replace('""', '"')

        extended_char_info.masked_description = masked_desc

    def generate_mask_desc_dataset(self) -> List[dict]:
        inds = sorted(list(self.char_infos.keys()))
        data: List[dict] = []
        for i, ind in enumerate(inds):
            print(f'masking {i+1} / {len(inds)} ...', end='\r')
            char_info = self.char_infos[ind]
            extended_char_info = (
                ExtendedCharacterInfo.
                from_full_character_info(char_info)
            )
            masked_description = self.get_masked_description(ind)
            extended_char_info.masked_description = masked_description
            self.post_static_clean_mask_desc(extended_char_info)
            data.append(extended_char_info.to_dict())
        return data

    def debug(self):
        i = 10000
        print(self.char_infos[i].description)
        print()
        print(self.get_masked_description(i))

        # tokens, mapping = self.coref_char[0].get_tokens()
        # raw_tokens = self.coref_char[0].tokens
        # for i, j in enumerate(mapping):
        #     if j is None: continue
        #     print(tokens[j])
        #     print(raw_tokens[i])
        #     print()
        #     a = input()

        # for i in self.coref_char.indices():
        #     tokens, _ = self.coref_char[i].get_tokens()
        #     orig_tokens, valid_tokens, mapping = (
        #         CharDataTransformer.
        #         extract_orig_description_tokens(
        #             self.char_infos[i].description,
        #         )
        #     )
        #     if len(valid_tokens) != len(tokens):
        #         found = False
        #         for t1, t2 in zip(tokens, valid_tokens):
        #             if t1 != t2:
        #                 found = True
        #                 break
                
        #         if not found: continue
                
        #         print(f'book {i}')
        #         print(orig_tokens)
        #         print(valid_tokens)
        #         print(tokens)
        #         for t1, t2 in zip(tokens, valid_tokens):
        #             print(t1)
        #             print(t2)
        #             print()
        #             a = input()
        #             if a == 's': break
        #         print(tokens)
        #         print(valid_tokens)

import logging
import nltk
from dataclasses import dataclass

from data_center import DataCenter
from data_center_coref import CorefDataCenter

logging.basicConfig(
    filename='main.log',
    level=logging.DEBUG,
)

@dataclass
class DataTransformer(object):
    orig_data: DataCenter
    coref_data: CorefDataCenter

    def get_shared_inds(self):
        orig_inds = set(self.orig_data.merged_original_books.keys())
        coref_inds = set(self.coref_data.merged_coref_books.keys())
        return sorted(list(coref_inds & orig_inds))

    def __check_book_inds(self):
        orig_inds = list(self.orig_data.merged_original_books.keys())
        coref_inds = list(self.coref_data.merged_coref_books.keys())

        left_diff = list(set(orig_inds) - (set(coref_inds)))
        left_diff.sort()

        right_diff = list(set(coref_inds) - (set(orig_inds)))
        right_diff.sort()

        if len(left_diff) > 0:
            logging.debug(
                f'Original data has {len(left_diff)} more books '
                f'- {", ".join(left_diff)}',
            )

        if len(right_diff) > 0:
            logging.debug(
                f'Coref data has {len(right_diff)} more books '
                f'- {", ".join(right_diff)}',
            )

    def __check_num_sentence(self, i):
        orig_summary = self.orig_data.get_sentence_based_summary(i)
        coref_summary = self.coref_data.get_token_based_summary(i)
        if len(orig_summary) != len(coref_summary):
            logging.debug(
                f'Original book {i}\'s summary has {len(orig_summary)} '
                f'sentences, but coref book {i}\'s summary has '
                f'{len(coref_summary)}',
            )
        
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
                    ' '.join(coref_summary[j]) if 0 <= j < l2
                    else ''
                )
                print(f'Book {i}')
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
                

    def validate(self):
        self.__check_book_inds()
        for i in self.get_shared_inds():
            self.__check_num_sentence(i)
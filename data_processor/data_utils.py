from dataclasses import dataclass, field
from typing import List, Callable, Dict, Optional, Set, TextIO, Tuple

import numpy as np
from collections import Counter
from numpy.linalg import norm
from rouge import Rouge

import nltk
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer

from .orig_utils import OrigBook
from .coref_utils import CorefBook, CorefReference

# download nltk data for parsing sentences
nltk.download('wordnet')

lemmatizer = WordNetLemmatizer()

MALE_PRONOUNS = ['he', 'his', 'him', 'himself']
FEMALE_PRONOUNS = ['she', 'her', 'herself']

def get_pos_tag(word: str):
    tag = nltk.pos_tag([word])[0][1]
    if tag.startswith('J'): return wordnet.ADJ
    if tag.startswith('V'): return wordnet.VERB
    if tag.startswith('R'): return wordnet.ADV
    return wordnet.NOUN

# Longest common subsequence
def lcs(s1: List[str], s2: List[str]):
    n1, n2 = len(s1), len(s2) 
    dp: List[List[int]] = [
        [0 for _ in range(n2+1)] for _ in range(n1+1)
    ]
  
    for i in range(n1+1): 
        for j in range(n2+1): 
            if i == 0 or j == 0: dp[i][j] = 0
            elif s1[i-1] == s2[j-1]: dp[i][j] = dp[i-1][j-1]+1
            else: dp[i][j] = max(dp[i-1][j] , dp[i][j-1]) 

    return dp[n1][n2]

def tokenize(
    text: str,
    use_lemmatizer: bool=False,
    remove_stopwords: bool=False,
) -> List[str]:
    lemma_func: Callable[[str], str] = lambda w: w
    if use_lemmatizer:
        lemma_func = lambda w: lemmatizer.lemmatize(w, pos=get_pos_tag(w))

    text = text.lower()
    pure_word_tokenizer = nltk.RegexpTokenizer(r'\w+')
    tokens: List[str] = list(map(
        lemma_func,
        pure_word_tokenizer.tokenize(text),
    ))

    sw: List[str] = (
        stopwords.words('english') if remove_stopwords
        else []
    )
    tokens = list(filter(lambda w: w not in sw, tokens))

    return tokens
    
def calc_similarity(
    s1_tokens: List[str],
    s2_tokens: List[str],
) -> float:
    s1_set, s2_set = set(s1_tokens), set(s2_tokens)
    
    if len(s1_set) == 0 or len(s2_set) == 0:
        return 0.0

    rvector = list(s1_set | s2_set)
    l1 = np.zeros(len(rvector))
    l2 = np.zeros(len(rvector))
    for i, w in enumerate(rvector):
        if w in s1_set: l1[i] = 1
        if w in s2_set: l2[i] = 1
    
    return np.dot(l1, l2) / (norm(l1) * norm(l2))

# Calculate Rouge-1 score
def calc_rouge_1(
    s1_tokens: List[str],
    s2_tokens: List[str],
) -> Dict[str, float]:
    left_score = right_score = 0.0
    if len(s1_tokens) > 0 and len(s2_tokens) > 0:
        shared_tokens = list(
            (Counter(s1_tokens) & Counter(s2_tokens)).elements(),
        )
        left_score = len(shared_tokens) / len(s1_tokens)
        right_score = len(shared_tokens) / len(s2_tokens)

    return {
        'left_score': left_score,
        'right_score': right_score,
    }

# Calculate Rouge-2 score (will use Rouge-1 if either inputs have length 1)
def calc_rouge_2(
    s1_tokens: List[str],
    s2_tokens: List[str],
) -> Dict[str, float]:
    s1_bigrams = [
        f'{w1}|{w2}' for w1, w2 in zip(s1_tokens[:-1], s1_tokens[1:])
    ]
    s2_bigrams = [
        f'{w1}|{w2}' for w1, w2 in zip(s2_tokens[:-1], s2_tokens[1:])
    ]

    left_score = right_score = 0.0

    if len(s1_bigrams) == 0 or len(s2_bigrams) == 0:
        return calc_rouge_1(s1_tokens, s2_tokens)

    shared_bigrams = list(
        (Counter(s1_bigrams) & Counter(s2_bigrams)).elements(),
    )
    left_score = len(shared_bigrams) / len(s1_bigrams)
    right_score = len(shared_bigrams) / len(s2_bigrams)

    return {
        'left_score': left_score,
        'right_score': right_score,
    }

# Calculate Rouge-L score
def calc_rouge_L(
    s1_tokens: List[str],
    s2_tokens: List[str],
) -> Dict[str, float]:
    left_score = right_score = 0.0

    if len(s1_tokens) > 0 and len(s2_tokens) > 0:
        lcs_size = lcs(s1_tokens, s2_tokens)
        left_score = lcs_size / len(s1_tokens)
        right_score = lcs_size / len(s2_tokens)

    return {
        'left_score': left_score,
        'right_score': right_score,
    }

# Calculate Rouge-L score
def calc_rouge_between_text(
    s1: str,
    s2: str,
) -> Dict[str, Dict[str, float]]:
    rouge = Rouge()
    scores: Dict[str, Dict[str, float]] = rouge.get_scores(s1, s2)[0]

    return {
        'rouge-1': {
            'left_score': scores['rouge-1']['r'],
            'right_score': scores['rouge-1']['p'],
        },
        'rouge-2': {
            'left_score': scores['rouge-2']['r'],
            'right_score': scores['rouge-2']['p'],
        },
        'rouge-l': {
            'left_score': scores['rouge-l']['r'],
            'right_score': scores['rouge-l']['p'],
        },
    }

class ThresholdCounter(object):
    def __init__(
        self,
        thresholds: List[float]=[
            0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
        ],
        base_threshold: float=0.0,
    ):
        self.counter: Dict[float, int] = {t: 0 for t in thresholds}
        self.base = base_threshold

    def add(self, val: float):
        for threshold in self.counter.keys():
            if val >= threshold:
                self.counter[threshold] += 1

    def print(self, out_file: Optional[TextIO]=None):
        print('Threshold, Counter', file=out_file)
        vals = sorted(list(self.counter.keys()))
        for val in vals:
            perc = 100 * self.counter[val] / self.counter[self.base]
            print(
                f'{val},\t{self.counter[val]},\t{perc:.2f} %',
                file=out_file,
            )

@dataclass
class MergedBook:
    orig_info: OrigBook
    coref_info: CorefBook

    @property
    def book_ind(self) -> int:
        return self.orig_info.book_info.book_ind
    
    @property
    def num_characters(self) -> int:
        return len(self.orig_info.characters)

    @staticmethod
    def get_match_score(name: str, mention: str) -> float:
        name_tokens = tokenize(name, use_lemmatizer=True)
        mention_tokens = tokenize(mention, use_lemmatizer=True)
        return calc_rouge_L(mention_tokens, name_tokens)['right_score']

    def get_coref_truncated_summary(self) -> Dict[str, str]:
        summary_sents = self.orig_info.get_sentence_based_summary()
        refs = self.coref_info.get_token_based_references()
        char_names = list(self.orig_info.characters.keys())
        
        char_summs: Dict[str, str] = {}

        for name in char_names:
            print(name, end='\r')
            s_inds = set()
            for ref in refs:
                max_score = 0.0
                for mention_tokens, _ in ref:
                    mention = ' '.join(mention_tokens)
                    score = MergedBook.get_match_score(name, mention)
                    max_score = max(max_score, score)
                    if max_score >= 0.5: break
            
                if max_score < 0.5: continue
                for _, s_ind in ref:
                    s_inds.add(s_ind)

            trunc_summ_sents = [
                summary_sents[ind]
                for ind in sorted(list(s_inds))
            ]
            char_summs[name] = ' '.join(trunc_summ_sents)

        return char_summs

    def get_summ_gender_count(self, target_chars: List[str]) -> Dict[str, Tuple[int, int, int]]:
        refs = self.coref_info.get_token_based_references()
        char_names = list(self.orig_info.characters.keys())
        
        char_genders: Dict[str, Tuple[int, int, int]] = {}

        for name in char_names:
            if name not in target_chars: continue
            print(name, end='\r')
            male_count = 0
            female_count = 0
            mention_count = 0
            for ref in refs:
                max_score = 0.0
                temp_male_count = 0
                temp_female_count = 0
                temp_mention_count = 0
                for mention_tokens, _ in ref:
                    mention = ' '.join(mention_tokens)
                    mm = mention.strip().lower()
                    if mm in MALE_PRONOUNS:
                        temp_male_count += 1
                    if mm in FEMALE_PRONOUNS:
                        temp_female_count += 1
                    temp_mention_count += 1
                    score = MergedBook.get_match_score(name, mention)
                    max_score = max(max_score, score)
            
                if max_score < 0.5: continue
                male_count += temp_male_count
                female_count += temp_female_count
                mention_count += temp_mention_count

            char_genders[name] = (male_count, female_count, mention_count)

        return char_genders

    def get_flattened_references(self) -> List[str]:
        refs = self.coref_info.get_token_based_references()
        flat_refs: List[str] = []
        for ref in refs:
            for mention in ref:
                flat_refs.append(' '.join(mention[0]))
        return flat_refs

    def get_ref_char_similarity(self) -> Dict[str, float]:
        similarity: Dict[str, float] = {}
        ref_token_group = [
            tokenize(ref, use_lemmatizer=True)
            for ref in self.get_flattened_references()
        ]

        for char_name in self.orig_info.characters.keys():
            name_tokens = tokenize(char_name, use_lemmatizer=True)
            sim_score = 0.0
            for ref_tokens in ref_token_group:
                sim_score = max(
                    sim_score,
                    calc_similarity(ref_tokens, name_tokens),
                )
            similarity[char_name] = sim_score

        return similarity

    def get_summ_desc_similarity(self) -> Dict[str, float]:
        similarity: Dict[str, float] = {}
        summary = self.orig_info.book_info.summary_text
        summary_tokens = tokenize(summary, use_lemmatizer=True)

        for name, info in self.orig_info.characters.items():
            desc = info.description_text
            desc_tokens = tokenize(desc, use_lemmatizer=True)
            similarity[name] = calc_similarity(
                summary_tokens,
                desc_tokens,
            )
        
        return similarity

    def get_summ_char_matchness(self) -> Dict[str, Dict[str, float]]:
        matchness: Dict[str, Dict[str, float]] = {}
        summary = self.orig_info.book_info.summary_text
        summary_tokens = tokenize(
            summary,
            use_lemmatizer=True,
            remove_stopwords=True,
        )

        for char_name in self.orig_info.characters.keys():
            name_tokens = tokenize(char_name, use_lemmatizer=True)
            # r1 = calc_rouge_1(summary_tokens, name_tokens)
            # r2 = calc_rouge_2(summary_tokens, name_tokens)
            rL = calc_rouge_L(summary_tokens, name_tokens)

            matchness[char_name] = {
                # 'rouge-1': r1['right_score'],
                # 'rouge-2': r2['right_score'],
                'rouge-l': rL['right_score'],
            }

        return matchness

    def get_summ_desc_matchness(self) -> Dict[str, Dict[str, float]]:
        matchness: Dict[str, Dict[str, float]] = {}
        summary = self.orig_info.book_info.summary_text

        for name, info in self.orig_info.characters.items():
            desc = info.description_text
            scores = calc_rouge_between_text(summary, desc)

            matchness[name] = {
                'rouge-1': scores['rouge-1']['right_score'],
                'rouge-2': scores['rouge-2']['right_score'],
                'rouge-l': scores['rouge-l']['right_score'],
            }

        return matchness

@dataclass
class ScoreDetail(object):
    sim_score: Optional[float] = None
    rouge_1: Optional[float] = None
    rouge_2: Optional[float] = None
    rouge_l: Optional[float] = None

    def to_dict(self) -> Dict[str, float]:
        data: Dict[str, float] = {}
        if self.sim_score is not None:
            data['sim'] = self.sim_score
        if self.rouge_1 is not None:
            data['rouge-1'] = self.rouge_1
        if self.rouge_2 is not None:
            data['rouge-2'] = self.rouge_2
        if self.rouge_l is not None:
            data['rouge-l'] = self.rouge_l
        return data

    @classmethod
    def from_dict(cls, d):
        return cls(
            sim_score=d.get('sim', None),
            rouge_1=d.get('rouge-1', None),
            rouge_2=d.get('rouge-2', None),
            rouge_l=d.get('rouge-l', None),
        )

@dataclass
class FullCharacterInfo(object):
    character_name: str
    book_title: str
    source: str
    summary: str
    description: str
    character_order: int

    sim_score: Optional[float] = None
    rouge_l: Optional[float] = None
    score_details: Dict[str, ScoreDetail] = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = {
            'character_name': self.character_name,
            'book_title': self.book_title,
            'source': self.source,
            'summary': self.summary,
            'description': self.description,
            'character_order': self.character_order,
            'score_details': {
                key: score_detail.to_dict()
                for key, score_detail in self.score_details.items()
            },
        }
        if self.sim_score is not None:
            data['sim_score'] = self.sim_score
        if self.rouge_l is not None:
            data['rouge-l'] = self.rouge_l
        return data

    @classmethod
    def from_dict(cls, d):
        return cls(
            **{
                key: val for key, val in d.items()
                if key not in ['score_details', 'rouge-l']
            },
            rouge_l=d.get('rouge-l', None),
            score_details={
                name: ScoreDetail.from_dict(info)
                for name, info in d['score_details'].items()
            },
        )

@dataclass
class ExtendedCharacterInfo(object):
    character_name: str
    book_title: str
    source: str
    summary: str
    description: str
    masked_description: str
    character_order: int

    sim_score: Optional[float] = None
    rouge_l: Optional[float] = None
    score_details: Dict[str, ScoreDetail] = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = {
            'character_name': self.character_name,
            'book_title': self.book_title,
            'source': self.source,
            'summary': self.summary,
            'description': self.description,
            'masked_description': self.masked_description,
            'character_order': self.character_order,
            'score_details': {
                key: score_detail.to_dict()
                for key, score_detail in self.score_details.items()
            },
        }
        if self.sim_score is not None:
            data['sim_score'] = self.sim_score
        if self.rouge_l is not None:
            data['rouge-l'] = self.rouge_l
        return data

    @classmethod
    def from_dict(cls, d):
        return cls(
            **{
                key: val for key, val in d.items()
                if key not in ['score_details', 'rouge-l']
            },
            rouge_l=d.get('rouge-l', None),
            score_details={
                name: ScoreDetail.from_dict(info)
                for name, info in d['score_details'].items()
            },
        )

    @classmethod
    def from_full_character_info(cls, char_info: FullCharacterInfo):
        d = char_info.to_dict()
        d['masked_description'] = ''
        return cls.from_dict(d)
import numpy as np
from numpy.linalg import norm

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

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

def calc_shared_ratio(s1, s2, lemma_func=lambda w: w):
    s1_tokens = [lemma_func(w) for w in word_tokenize(s1)]
    s2_tokens = [lemma_func(w) for w in word_tokenize(s2)]
    sw = stopwords.words('english')

    s1_set = {w for w in s1_tokens if not w in sw}
    s2_set = {w for w in s2_tokens if not w in sw}
    if len(s1_set) == 0 or len(s2_set) == 0:
        return 0.0

    return len(s1_set & s2_set) / len(s2_set)
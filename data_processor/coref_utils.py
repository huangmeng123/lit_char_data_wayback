from dataclasses import dataclass
from typing import List, Tuple, Optional

COREF_CONTROL_TOKENS = ['[SPL]', '[SEP]', '[CLS]']

@dataclass
class CorefSection:
    pid: int
    sid: int
    tokens: List[str] # sentences
    token_to_sentence: List[int] # sentence_map
    token_to_subtoken: List[int] # subtoken_map
    references: List[List[List[int]]] # predcted_clusters

    @classmethod
    def from_json(cls, data):
        pid, sid = map(int, data['doc_index'].split('-'))
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
            pid=pid,
            sid=sid,
            tokens=tokens,
            token_to_sentence=token_to_sentence,
            token_to_subtoken=token_to_subtoken,
            references=references,
        )

IndexRange = Tuple[int, int]
CorefMention = Tuple[List[str], int]
CorefReference = List[CorefMention]

def clean_coref_sentence(
    raw_sent: List[str],
) -> Tuple[List[str], List[Optional[int]]]:
    sent: List[str] = []
    buf: Optional[str] = None
    mapping: List[Optional[int]] = []
    temp_count: int = 0
    for token in raw_sent:
        if token.startswith('##'):
            temp_count += 1
            if buf is None:
                buf = token
            else:
                buf += token[2:]
        else:
            if buf in COREF_CONTROL_TOKENS:
                for _ in range(temp_count): mapping.append(None)
            elif buf is not None:
                sent.append(buf)
                for _ in range(temp_count): mapping.append(len(sent)-1)
            buf = token
            temp_count = 1
    if buf in COREF_CONTROL_TOKENS:
        for _ in range(temp_count): mapping.append(None)
    elif buf is not None:
        sent.append(buf)
        for _ in range(temp_count): mapping.append(len(sent)-1)
    return sent, mapping

@dataclass
class CorefParagraph:
    pid: int # paragraph ID
    tokens: List[str]
    token_to_sentence: List[int]
    num_sentences: int
    token_to_subtoken: List[int]
    num_subtokens: int
    references: List[List[IndexRange]]

    def get_tokens(self) -> Tuple[List[str], List[Optional[int]]]:
        tokens, mapping = clean_coref_sentence(self.tokens)
        return tokens, mapping

    def get_token_based_sentences(self) -> List[List[str]]:
        tokens = self.tokens
        num_tokens = len(tokens)
        token2sent = self.token_to_sentence
        num_sents = self.num_sentences

        breaks: List[int] = []
        for i in range(num_sents):
            breaks.append(token2sent.index(i))
        breaks.append(num_tokens)
        sents = [tokens[i:j] for i, j in zip(breaks[:-1], breaks[1:])]

        merged_sents: List[List[str]] = []
        for sent in sents:
            merged_sent, _ = clean_coref_sentence(sent)
            merged_sents.append(merged_sent)
        return merged_sents

    def get_tokens_with_sentence_index(self) -> List[Tuple[str, int]]:
        sents = self.get_token_based_sentences()
        tokens: List[Tuple[str, int]] = []
        for i, sent in enumerate(sents):
            sent_tokens = [(token, i) for token in sent]
            tokens.extend(sent_tokens)
        return tokens

    def get_sentence_based_summary(self) -> List[str]:
        return [
            ' '.join(filter(
                lambda w: w not in COREF_CONTROL_TOKENS,
                sent,
            )) for sent in self.get_token_based_sentences()
        ]

    def get_readable_content(self) -> str:
        return '\n'.join(self.get_sentence_based_summary())

    def get_token_based_references(self) -> List[CorefReference]:
        tokens = self.tokens
        token2sent = self.token_to_sentence

        raw_refs: List[CorefReference] = [
            [(tokens[a:b+1], token2sent[a]) for a, b in ref]
            for ref in self.references
        ]
        refs: List[CorefReference] = []
        for raw_ref in raw_refs:
            ref = []
            for raw_mention_tokens, sent_ind in raw_ref:
                mention_tokens, _ = clean_coref_sentence(
                    raw_mention_tokens,
                )
                ref.append((mention_tokens, sent_ind))
            refs.append(ref)
        return refs

CorefBook = CorefParagraph
CorefCharacter = CorefParagraph

from typing import List, Dict, Optional

import json

from .coref_utils import CorefSection, CorefParagraph

class CorefResultReader(object):
    @staticmethod
    def merge_section_cluster(
        cluster: Dict[int, CorefSection],
    ) -> CorefParagraph:
        pg = CorefParagraph(
            pid=0,
            tokens=[],
            token_to_sentence=[],
            num_sentences=0,
            token_to_subtoken=[],
            num_subtokens=0,
            references=[],
        )

        num_tokens = 0
        sids = list(cluster.keys())
        sids.sort()
        pid: Optional[int] = None
        for sid in sids:
            section = cluster[sid]

            if pid is None:
                pid = section.pid
            else:
                assert(pid == section.pid)
            
            pg.tokens.extend(section.tokens)

            pg.token_to_sentence.extend(
                [i+pg.num_sentences for i in section.token_to_sentence],
            )
            pg.num_sentences = max(pg.token_to_sentence) + 1

            pg.token_to_subtoken.extend(
                [i+pg.num_subtokens for i in section.token_to_subtoken],
            )
            pg.num_subtokens = max(pg.token_to_subtoken) + 1

            pg.references.extend([
                [(a+num_tokens, b+num_tokens) for a, b in ref]
                for ref in section.references
            ])

            num_tokens = len(pg.tokens)

        assert(len(pg.token_to_sentence) == num_tokens)
        assert(len(pg.token_to_subtoken) == num_tokens)
        
        assert(pid is not None)
        pg.pid = pid

        return pg

    @staticmethod
    def merge_sections(
        sections: List[CorefSection],
    ) -> Dict[int, CorefParagraph]:
        section_clusters: Dict[int, Dict[int, CorefSection]] = {}
        for section in sections:
            pid, sid = section.pid, section.sid
            cluster = section_clusters.get(pid, {})
            cluster[sid] = section
            section_clusters[pid] = cluster

        paragraphs: Dict[int, CorefParagraph] = {}
        for pid, cluster in section_clusters.items():
            paragraph = CorefResultReader.merge_section_cluster(cluster)
            paragraphs[pid] = paragraph

        return paragraphs
    
    def __init__(self, sections: List[CorefSection]):
        self.paragraphs = CorefResultReader.merge_sections(sections)
    
    @classmethod
    def build_from_file(cls, filename: str):
        sections: List[CorefSection] = []
        with open(filename) as json_file:
            for line in json_file.readlines():
                data = json.loads(line)
                section = CorefSection.from_json(data)
                sections.append(section)
        return cls(sections)

    def __getitem__(self, pid: int):
        return self.paragraphs[pid]

    def __len__(self):
        return len(self.paragraphs)
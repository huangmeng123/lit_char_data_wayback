import difflib
from typing import Generic, List, Tuple, TypeVar
from dataclasses import dataclass

IndRange = Tuple[int, int]

_T = TypeVar('_T', str, List[str])
@dataclass
class TextDiff(Generic[_T]):
    texts: Tuple[_T, _T]
    ind_ranges: List[Tuple[IndRange, IndRange]]

    def get_forward_changes(self) -> List[Tuple[IndRange, _T]]:
        forward_changes: List[Tuple[IndRange, _T]] = []
        for ind_range1, ind_range2 in self.ind_ranges:
            s, e = ind_range2
            forward_changes.append((
                ind_range1,
                self.texts[1][s:e],
            ))
        return forward_changes
    
    def get_backward_changes(self) -> List[Tuple[_T, IndRange]]:
        backward_changes: List[Tuple[_T, IndRange]] = []
        for ind_range1, ind_range2 in self.ind_ranges:
            s, e = ind_range1
            backward_changes.append((
                self.texts[0][s:e],
                ind_range2,
            ))
        return backward_changes

    def get_changes(self) -> List[Tuple[_T, _T]]:
        changes: List[Tuple[_T, _T]] = []
        for ind_range1, ind_range2 in self.ind_ranges:
            s1, e1 = ind_range1
            s2, e2 = ind_range2
            changes.append((
                self.texts[0][s1:e1],
                self.texts[1][s2:e2],
            ))
        return changes

class TextDiffTool(object):
    @staticmethod
    def diff_text(text1: str, text2: str) -> TextDiff[str]:
        signs = [s[0] for s in difflib.ndiff(text1, text2)]
        ind_ranges: List[Tuple[IndRange, IndRange]] = []
        neg_count, pos_count = 0, 0
        neg_ind, pos_ind = 0, 0
        for sign in signs:
            if sign == ' ':
                if neg_count > 0 or pos_count > 0:
                    ind_ranges.append((
                        (neg_ind-neg_count, neg_ind),
                        (pos_ind-pos_count, pos_ind),
                    ))
                    neg_count, pos_count = 0, 0
                neg_ind += 1
                pos_ind += 1
            elif sign == '-':
                neg_count += 1
                neg_ind += 1
            elif sign == '+':
                pos_count += 1
                pos_ind += 1
        if neg_count > 0 or pos_count > 0:
            ind_ranges.append((
                (neg_ind-neg_count, neg_ind),
                (pos_ind-pos_count, pos_ind),
            ))
        return TextDiff[str](
            texts=(text1, text2),
            ind_ranges=ind_ranges,
        )

    @staticmethod
    def diff_list(
        list1: List[str], list2: List[str]
    ) -> TextDiff[List[str]]:
        signs = [s[0] for s in difflib.ndiff(list1, list2)]
        ind_ranges: List[Tuple[IndRange, IndRange]] = []
        neg_count, pos_count = 0, 0
        neg_ind, pos_ind = 0, 0
        for sign in signs:
            if sign == ' ':
                if neg_count > 0 or pos_count > 0:
                    ind_ranges.append((
                        (neg_ind-neg_count, neg_ind),
                        (pos_ind-pos_count, pos_ind),
                    ))
                    neg_count, pos_count = 0, 0
                neg_ind += 1
                pos_ind += 1
            elif sign == '-':
                neg_count += 1
                neg_ind += 1
            elif sign == '+':
                pos_count += 1
                pos_ind += 1
        if neg_count > 0 or pos_count > 0:
            ind_ranges.append((
                (neg_ind-neg_count, neg_ind),
                (pos_ind-pos_count, pos_ind),
            ))
        return TextDiff[List[str]](
            texts=(list1, list2),
            ind_ranges=ind_ranges,
        )

    @staticmethod
    def restore_text(
        text: str,
        changes: List[Tuple[IndRange, str]],
    ) -> str:
        restored_text = ''
        prev_e = 0
        for (s, e), token in changes:
            restored_text += text[prev_e:s] + token
            prev_e = e
        restored_text += text[prev_e:]
        return restored_text

    @staticmethod
    def restore_list(
        text_list: List[str],
        changes: List[Tuple[IndRange, List[str]]],
    ) -> List[str]:
        restored_list = []
        prev_e = 0
        for (s, e), token in changes:
            restored_list += text_list[prev_e:s] + token
            prev_e = e
        restored_list += text_list[prev_e:]
        return restored_list

    @staticmethod
    def restore_list_from_text(
        text: str,
        changes: List[Tuple[IndRange, List[str]]],
    ) -> List[str]:
        text_list = text.split(' ')
        return TextDiffTool.restore_list(text_list, changes)
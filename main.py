from data_processor.orig_utils import OrigBook
from random import choice
from data_processor.data_utils import FullCharacterInfo
from typing import List, Dict, Tuple, Any

import json
import random
import csv
import sys

from data_processor.orig_data_center import OrigBookDataCenter
from data_processor.coref_data_center import CorefBookDataCenter
from data_processor.data_transformer import BookDataTransformer
from data_processor.data_transformer import print_score_stats_from_dataset_file
from data_processor.data_transformer import CharDataTransformer

def export_dataset_as_jsonl(data: List[dict], filename: str):
    with open(filename, 'w') as out_file:
        for d in data:
            json.dump(d, out_file)
            out_file.write('\n')

def load_dataset_from_jsonl(filename: str) -> List[dict]:
    dataset: List[dict] = []
    with open(filename) as in_file:
        for line in in_file.readlines():
            d = json.loads(line)
            dataset.append(d)
    return dataset

def filter_data_by_name(data: List[dict]) -> List[dict]:
    return [
        d for d in data
        if d['score_details']['name']['rouge-l'] >= 0.6
        or d['character_order'] < 3
    ]

def filter_data_by_desc(data: List[dict]) -> List[dict]:
    return [
        d for d in data
        if d['character_order'] < 3
        or d['score_details']['description']['rouge-l'] >= 0.2
    ]

def split_data(
    data: List[dict],
) -> Tuple[List[dict], List[dict], List[dict]]:
    book_to_chars: Dict[str, List[dict]] = {}
    for d in data:
        key = d['book_title']
        sub_data = book_to_chars.get(key, [])
        sub_data.append(d)
        book_to_chars[key] = sub_data

    titles = list(book_to_chars.keys())
    i, count, total = 0, 0, len(data)

    train_data: List[dict] = []
    while i < len(titles):
        sub_data = book_to_chars[titles[i]]
        train_data.extend(sub_data)
        i += 1
        prev_count, count = count, count + len(sub_data)
        if prev_count < 0.8 * total and count >= 0.8 * total:
            break
    
    test_data: List[dict] = []
    while i < len(titles):
        sub_data = book_to_chars[titles[i]]
        test_data.extend(sub_data)
        i += 1
        prev_count, count = count, count + len(sub_data)
        if prev_count < 0.9 * total and count >= 0.9 * total:
            break
    
    val_data: List[dict] = []
    while i < len(titles):
        sub_data = book_to_chars[titles[i]]
        val_data.extend(sub_data)
        i += 1

    return train_data, test_data, val_data

def filter_data(
    filename1: str,
    filename2: str,
    filename_train: str,
    filename_test: str,
    filename_val: str,
):
    # with open(filename) as in_file:
    #     data: List[Dict[str, Any]] = json.load(in_file)

    data1: List[Dict[str, Any]] = []
    with open(filename1) as in_file:
        for d in in_file.readlines():
            data1.append(json.loads(d))

    # data1 = [
    #     d for d in data
    #     if d['score_details']['name']['rouge-l'] >= 0.6
    #     or d['character_order'] < 3
    # ]

    data2 = [
        d for d in data1
        if d['score_details']['description']['rouge-l'] >= 0.2
    ]
    export_dataset_as_jsonl(data2, filename2)

    book_to_chars = {}
    for d in data2:
        key = d['book_title']
        sub_data = book_to_chars.get(key, [])
        sub_data.append(d)
        book_to_chars[key] = sub_data

    titles = list(book_to_chars.keys())
    i, count, total = 0, 0, len(data2)
    with open(filename_train, 'w') as out_f:
        while i < len(titles):
            sub_data = book_to_chars[titles[i]]
            for d in sub_data:
                json.dump(d, out_f)
                out_f.write('\n')
            i += 1
            prev_count, count = count, count + len(sub_data)
            if prev_count < 0.8 * total and count >= 0.8 * total:
                break
    print(count)
    
    with open(filename_test, 'w') as out_f:
        while i < len(titles):
            sub_data = book_to_chars[titles[i]]
            for d in sub_data:
                json.dump(d, out_f)
                out_f.write('\n')
            i += 1
            prev_count, count = count, count + len(sub_data)
            if prev_count < 0.9 * total and count >= 0.9 * total:
                break
    print(count)
    
    with open(filename_val, 'w') as out_f:
        while i < len(titles):
            sub_data = book_to_chars[titles[i]]
            for d in sub_data:
                json.dump(d, out_f)
                out_f.write('\n')
            i += 1
            count += len(sub_data)
    print(count)


version = 'v03'
truncated_dirname = 'truncated_datasets/'
mask_dirname = 'mask_datasets/'
data_root_path = f'/home/huangme-pop/lit_char_data/data/{version}/'
raw_data_filename = (
    data_root_path +
    f'original-book-export-from-database_{version}.json'
)
coref_input_filename = (
    data_root_path +
    f'coref_input_{version}.tsv'
)
coref_input_txt_filename = (
    data_root_path +
    f'coref_input_{version}.txt'
)
coref_summary_filename = (
    data_root_path +
    f'coref_results_summaries_{version}.json'
)
coref_desc_filename = (
    data_root_path +
    f'coref_results_descriptions_{version}.json'
)
matchness_output_filename = (
    data_root_path +
    f'matchness_{version}.txt'
)
similarity_output_filename = (
    data_root_path +
    f'similarity_{version}.txt'
)
untruncated_character_dataset_filename = (
    data_root_path +
    f'untruncated_char_dataset_{version}.json'
)
untruncated_character_dataset_filter_by_name_filename = (
    data_root_path +
    f'untruncated_char_dataset_filter_by_name_{version}.json'
)
untruncated_character_dataset_filter_by_name_and_desc_filename = (
    data_root_path +
    f'untruncated_char_dataset_filter_by_name_and_description_{version}.json'
)
untruncated_character_dataset_filter_by_name_and_desc_train_filename = (
    data_root_path +
    f'untruncated_char_dataset_filter_by_name_and_description_train_{version}.jsonl'
)
untruncated_character_dataset_filter_by_name_and_desc_test_filename = (
    data_root_path +
    f'untruncated_char_dataset_filter_by_name_and_description_test_{version}.jsonl'
)
untruncated_character_dataset_filter_by_name_and_desc_val_filename = (
    data_root_path +
    f'untruncated_char_dataset_filter_by_name_and_description_val_{version}.jsonl'
)
untruncated_masked_character_dataset_filter_by_name_filename = (
    data_root_path + mask_dirname +
    f'untruncated_masked_char_dataset_filter_by_name_{version}.jsonl'
)
untruncated_masked_character_dataset_filter_by_name_and_desc_filename = (
    data_root_path + mask_dirname +
    f'untruncated_masked_char_dataset_filter_by_name_and_description_{version}.jsonl'
)
untruncated_masked_character_dataset_filter_by_name_and_desc_train_filename = (
    data_root_path + mask_dirname +
    f'untruncated_masked_char_dataset_filter_by_name_and_description_train_{version}.jsonl'
)
untruncated_masked_character_dataset_filter_by_name_and_desc_test_filename = (
    data_root_path + mask_dirname +
    f'untruncated_masked_char_dataset_filter_by_name_and_description_test_{version}.jsonl'
)
untruncated_masked_character_dataset_filter_by_name_and_desc_val_filename = (
    data_root_path + mask_dirname +
    f'untruncated_masked_char_dataset_filter_by_name_and_description_val_{version}.jsonl'
)
pure_truncated_character_dataset_filename = (
    data_root_path + truncated_dirname +
    f'pure_truncated_char_dataset.jsonl'
)
truncated_character_dataset_filename = (
    data_root_path + truncated_dirname +
    f'truncated_char_dataset.jsonl'
)
truncated_character_dataset_filter_by_name_filename = (
    data_root_path + truncated_dirname +
    f'truncated_char_dataset_filter_by_name.jsonl'
)
truncated_character_dataset_filter_by_name_and_desc_filename = (
    data_root_path + truncated_dirname +
    f'truncated_char_dataset_filter_by_name_and_description.jsonl'
)
truncated_character_dataset_filter_by_name_and_desc_train_filename = (
    data_root_path + truncated_dirname +
    f'truncated_char_dataset_filter_by_name_and_description_train.jsonl'
)
truncated_character_dataset_filter_by_name_and_desc_test_filename = (
    data_root_path + truncated_dirname +
    f'truncated_char_dataset_filter_by_name_and_description_test.jsonl'
)
truncated_character_dataset_filter_by_name_and_desc_val_filename = (
    data_root_path + truncated_dirname +
    f'truncated_char_dataset_filter_by_name_and_description_val.jsonl'
)


def original():

    # cdt = CharDataTransformer.build_from_file(
    #     full_char_filename=untruncated_character_dataset_filter_by_name_filename,
    #     coref_desc_filename=coref_desc_filename,
    # )

    # cdt.validate()
    # cdt.debug()

    # data = cdt.generate_mask_desc_dataset()
    # export_dataset_as_jsonl(
    #     data,
    #     untruncated_masked_character_dataset_filter_by_name_filename,
    # )

    # dc = OrigBookDataCenter.build_from_file(raw_data_filename)
    # dc.validate()

    # codc = CorefBookDataCenter.build_from_file(coref_summary_filename)
    # codc.validate()

    # bdt = BookDataTransformer.build_from_data_center(dc, codc)
    # bdt.validate()

    # pure_trunc_data = bdt.generate_truncated_summary_character_dataset()
    # export_dataset_as_jsonl(pure_trunc_data, pure_truncated_character_dataset_filename)

    pure_trunc_data = load_dataset_from_jsonl(pure_truncated_character_dataset_filename)

    with open(untruncated_character_dataset_filename) as in_file:
        data = json.load(in_file)

    # validate
    for trunc, full in zip(pure_trunc_data, data):
        assert(trunc['book_title'] == full['book_title'])
        assert(trunc['source'] == full['source'])
        assert(trunc['character_name'] == full['character_name'])

    # merge
    merged_data = []
    for trunc, full in zip(pure_trunc_data, data):
        char_info = FullCharacterInfo.from_dict(full)
        d = char_info.to_dict()
        d['coref_truncated_summary'] = trunc['coref_truncated_summary']
        merged_data.append(d)
    # export_dataset_as_jsonl(merged_data, truncated_character_dataset_filename)
    print(f'{len(merged_data)} truncated data')

    # filter by name
    filter_data1 = filter_data_by_name(merged_data)
    # export_dataset_as_jsonl(
    #     filter_data1,
    #     truncated_character_dataset_filter_by_name_filename,
    # )
    print(f'{len(filter_data1)} truncated data after filtering by name')

    # filter by description
    filter_data2 = filter_data_by_desc(filter_data1)
    # export_dataset_as_jsonl(
    #     filter_data2,
    #     truncated_character_dataset_filter_by_name_and_desc_filename,
    # )
    print(f'{len(filter_data2)} truncated data after filtering by name and description')

    # split dataset into train/test/val
    train_data, test_data, val_data = split_data(filter_data2)
    # export_dataset_as_jsonl(
    #     train_data,
    #     truncated_character_dataset_filter_by_name_and_desc_train_filename,
    # )
    # export_dataset_as_jsonl(
    #     test_data,
    #     truncated_character_dataset_filter_by_name_and_desc_test_filename,
    # )
    # export_dataset_as_jsonl(
    #     val_data,
    #     truncated_character_dataset_filter_by_name_and_desc_val_filename,
    # )
    print(f'{len(train_data)} train data')
    print(f'{len(test_data)} test data')
    print(f'{len(val_data)} val data')

def add_choice(data):
    prev = None
    buf = []
    books = []
    for d in data:
        key = (d['book_title'], d['source'])
        if key != prev:
            if prev is not None:
                books.append(buf)
            buf = [d]
            prev = key
        else:
            buf.append(d)
    books.append(buf)

    for book in books:
        choices = [char['character_name'] for char in book]
        random.shuffle(choices)
        for char in book:
            char['multichoice'] = {
                'choices': choices,
                'label': choices.index(char['character_name'])
            }
    
    chars = []
    for book in books:
        for char in book:
            chars.append(char)
    
    return chars

def add_choice_to_dataset():
    train_filename = untruncated_masked_character_dataset_filter_by_name_and_desc_train_filename
    test_filename = untruncated_masked_character_dataset_filter_by_name_and_desc_test_filename
    val_filename = untruncated_masked_character_dataset_filter_by_name_and_desc_val_filename
    
    train_data = load_dataset_from_jsonl(train_filename)
    test_data = load_dataset_from_jsonl(test_filename)
    val_data = load_dataset_from_jsonl(val_filename)

    train_data = add_choice(train_data)
    export_dataset_as_jsonl(train_data, train_filename)
    test_data = add_choice(test_data)
    export_dataset_as_jsonl(test_data, test_filename)
    val_data = add_choice(val_data)
    export_dataset_as_jsonl(val_data, val_filename)



def main():
    train_data = load_dataset_from_jsonl(untruncated_masked_character_dataset_filter_by_name_and_desc_train_filename)
    test_data = load_dataset_from_jsonl(untruncated_masked_character_dataset_filter_by_name_and_desc_test_filename)
    val_data = load_dataset_from_jsonl(untruncated_masked_character_dataset_filter_by_name_and_desc_val_filename)
    data = train_data + test_data + val_data

    target_chars: Dict[Tuple[str, str], List[str]] = {}
    for d in data:
        key = (d['book_title'], d['source'])
        chars = target_chars.get(key, [])
        chars.append(d['character_name'])
        target_chars[key] = chars

    odc = OrigBookDataCenter.build_from_file(raw_data_filename)
    cdc = CorefBookDataCenter.build_from_file(coref_summary_filename)
    bdt = BookDataTransformer.build_from_data_center(odc, cdc)
    gender_count = bdt.get_gender_count(target_chars)

    with open('gender_count2.csv', 'w') as out_f:
        writer = csv.writer(out_f, delimiter=',', quoting=csv.QUOTE_ALL)
        writer.writerow(['book_title', 'source', 'character_name', 'male_count', 'female_count', 'mention_count'])
        for (title, source), counter in gender_count.items():
            for name, (male, female, mention) in counter.items():
                writer.writerow([title, source, name, male, female, mention])

    # cdt = CharDataTransformer.build_from_file(
    #     full_char_filename=untruncated_character_dataset_filter_by_name_filename,
    #     coref_desc_filename=coref_desc_filename,
    # )

    # cdt.validate()
    # cdt.debug()

    # data = cdt.generate_mask_desc_dataset()
    # export_dataset_as_jsonl(
    #     data,
    #     untruncated_masked_character_dataset_filter_by_name_filename,
    # )
    
    # data = load_dataset_from_jsonl(untruncated_masked_character_dataset_filter_by_name_filename)
    
    # filter by description
    # filter_data1 = add_choice(filter_data_by_desc(data))
    # export_dataset_as_jsonl(
    #     add_choice(filter_data1),
    #     untruncated_masked_character_dataset_filter_by_name_and_desc_filename,
    # )
    # print(f'{len(filter_data1)} masked data after filtering by name and description')
    # for i in range(100):
    #     l = len(list(filter(lambda d: len(d['multichoice']['choices'])==(i+1), filter_data1)))
    #     if l > 0:
    #         print(f'{i+1} characters: {l / (i+1)} data points')

    # for d in add_choice(filter_data1):
    #     if 600 < len(d['summary']) < 1000:
    #         print(d['character_name'])
    #         print(d['multichoice']['choices'])
    #         print(d['summary'])
    #         print(d['masked_description'])
    #         _ = input()

    # # split dataset into train/test/val
    # train_data, test_data, val_data = split_data(filter_data1)
    # export_dataset_as_jsonl(
    #     add_choice(train_data),
    #     untruncated_masked_character_dataset_filter_by_name_and_desc_train_filename,
    # )
    # export_dataset_as_jsonl(
    #     add_choice(test_data),
    #     untruncated_masked_character_dataset_filter_by_name_and_desc_test_filename,
    # )
    # export_dataset_as_jsonl(
    #     add_choice(val_data),
    #     untruncated_masked_character_dataset_filter_by_name_and_desc_val_filename,
    # )
    # print(f'{len(train_data)} train data')
    # print(f'{len(test_data)} test data')
    # print(f'{len(val_data)} val data')

if __name__ == '__main__':
    main()
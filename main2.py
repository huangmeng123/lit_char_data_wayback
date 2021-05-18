from data_processor.orig_data_center import OrigBookDataCenter
from typing import List, Tuple, Dict

import json
import random
from datetime import datetime

VERSION = 'v03'
MASKED_DIRNAME = 'mask_datasets/'
TRUNCATED_DIRNAME = 'truncated_datasets/'
DATA_ROOT_DIRPATH = f'/home/huangme-pop/lit_char_data/data/{VERSION}/'

MASKED_CHARACTER_DATASET_FILTER_BY_NAME = (
    DATA_ROOT_DIRPATH + MASKED_DIRNAME +
    f'untruncated_masked_char_dataset_filter_by_name_{VERSION}.jsonl'
)
TRUNCATED_CHARACTER_DATASET_FILTER_BY_NAME = (
    DATA_ROOT_DIRPATH + TRUNCATED_DIRNAME +
    f'truncated_char_dataset_filter_by_name.jsonl'
)

def load_dataset_from_jsonl(filename: str) -> List[dict]:
    dataset: List[dict] = []
    with open(filename) as in_file:
        for line in in_file.readlines():
            d = json.loads(line)
            dataset.append(d)
    return dataset

def export_dataset_as_jsonl(data: List[dict], filename: str):
    with open(filename, 'w') as out_file:
        for d in data:
            json.dump(d, out_file)
            out_file.write('\n')

def filter_data_by_name(data: List[dict]) -> List[dict]:
    return [
        d for d in data
        if d['score_details']['name']['rouge-l'] >= 0.6
        or d['character_order'] < 3
    ]

def filter_data_by_desc(data: List[dict]) -> List[dict]:
    return [
        d for d in data
        if d['score_details']['description']['rouge-l'] >= 0.2
        or d['character_order'] < 3
    ]

def clean_description(description):
    description = description.strip()
    while description.endswith('Read an'):
        description = description[:-7].strip()
    return description

def clean_name(name):
    name = name.replace('\n', ' ')
    name = name.replace('%', ' ')
    name = ' '.join(name.strip().split())
    return name

def clean_data(data):
    new_data = []
    for d in data:
        d['description'] = clean_description(d['description'])
        if 'masked_description' in d:
            d['masked_description'] = clean_description(d['masked_description'])
        d['character_name'] = clean_name(d['character_name'])
        new_data.append(d)
    return new_data

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

def split_data(
    data: List[dict]
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

def process(data, dataset_name, include_choices=False):
    data = filter_data_by_desc(data)
    data = clean_data(data)
    if include_choices: data = add_choice(data)
    export_dataset_as_jsonl(
        data,
        f'data/v04/{dataset_name}.jsonl',
    )
    print(len(data))
    train_data, test_data, val_data = split_data(data)
    export_dataset_as_jsonl(
        train_data,
        f'data/v04/{dataset_name}_train.jsonl',
    )
    export_dataset_as_jsonl(
        test_data,
        f'data/v04/{dataset_name}_test.jsonl',
    )
    export_dataset_as_jsonl(
        val_data,
        f'data/v04/{dataset_name}_val.jsonl',
    )

def main():
    data = load_dataset_from_jsonl(
        MASKED_CHARACTER_DATASET_FILTER_BY_NAME,
    )
    process(data, 'masked_char_data_filtered_by_name_and_description', True)
    
    data = load_dataset_from_jsonl(
        TRUNCATED_CHARACTER_DATASET_FILTER_BY_NAME,
    )
    process(data, 'truncated_char_data_filtered_by_name_and_description')
    
if __name__ == '__main__':
    main()
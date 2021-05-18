from random import choice
from typing import List

import jinja2
import json
import random
import csv
import numpy as np

data_root_path = 'data/v03/'
mask_path = 'mask_datasets/'
untruncated_masked_character_dataset_filter_by_name_and_desc_filename = (
    data_root_path + mask_path +
    f'untruncated_masked_char_dataset_filter_by_name_and_description_v03.jsonl'
)

human_eval_data_filename = (
    'html_template/human_eval_data.csv'
)

def load_dataset_from_jsonl(filename: str) -> List[dict]:
    dataset: List[dict] = []
    with open(filename) as in_file:
        for line in in_file.readlines():
            d = json.loads(line)
            dataset.append(d)
    return dataset

def export_dataset_to_csv(filename: str, books: List[dict]):
    with open(filename, 'w', newline='') as out_f:
       writer = csv.writer(out_f, delimiter=',', quoting=csv.QUOTE_ALL)
       keys = list(books[0].keys())
       print(len(keys))
       writer.writerow(keys)
       for book in books:
           line = [book[key] for key in keys]
           print(len(line))
           writer.writerow(line)

def generate_human_eval_data(book: dict, char_names: List[str]) -> dict:
    char_infos: List[dict] = book['char_infos']
    selected = random.sample(char_infos, 5)
    choices = [char['character_name'] for char in selected]
    # if len(char_infos) > 4:
    #     selected = random.sample(char_infos, 5)
    # else:
    #     selected = char_infos
    # choices = [char['character_name'] for char in selected]
    # if len(choices) == 4:
    #     while True:
    #         extra = random.choice(char_names)
    #         if extra not in choices:
    #             choices.append(extra)
    #             break
    random.shuffle(choices)

    data = {
        'book_title': book['book_title'],
        'source': book['source'],
        'summary': book['summary'],

        'char1': selected[0]['character_name'],
        'char2': selected[1]['character_name'],
        'char3': selected[2]['character_name'],
        'char4': selected[3]['character_name'],

        'description1': selected[0]['description'],
        'description2': selected[1]['description'],
        'description3': selected[2]['description'],
        'description4': selected[3]['description'],

        'masked_description1': selected[0]['masked_description'],
        'masked_description2': selected[1]['masked_description'],
        'masked_description3': selected[2]['masked_description'],
        'masked_description4': selected[3]['masked_description'],

        'choice1': choices[0],
        'choice2': choices[1],
        'choice3': choices[2],
        'choice4': choices[3],
        'choice5': choices[4],
    }
    return data

def generate_human_eval_data2(book: dict) -> dict:
    char_infos: List[dict] = book['char_infos']
    selected = random.sample(char_infos, 4)

    data = {
        'book_title': book['book_title'],
        'source': book['source'],
        'summary': book['summary'],

        'char1': selected[0]['character_name'],
        'char2': selected[1]['character_name'],
        'char3': selected[2]['character_name'],
        'char4': selected[3]['character_name'],

        'description1': selected[0]['description'],
        'description2': selected[1]['description'],
        'description3': selected[2]['description'],
        'description4': selected[3]['description'],
    }
    return data

def human_eval1():
    data = load_dataset_from_jsonl(untruncated_masked_character_dataset_filter_by_name_and_desc_filename)
    # d = data[0]
    # print(d['character_name'])
    # print(d['multichoice'].values())

    # aggregate by book
    books = {}
    char_names = set()
    for d in data:
        key = (d['book_title'], d['source'])
        l = books.get(key, {
            'book_title': d['book_title'],
            'source': d['source'],
            'summary': d['summary'],
            'char_infos': [],
        })
        l['char_infos'].append({
            'character_name': d['character_name'],
            'description': d['description'],
            'masked_description': d['masked_description'].replace('[MASK]', '&#8287;&#8287;______&#8287;&#8287;'),
        })
        char_names.add(d['character_name'])
        books[key] = l

    # num_words = list(map(lambda b: len(b['summary'].split()), books.values()))
    # print(sum(num_words) / len(num_words))

    keys = list(filter(lambda k: 4 < len(books[k]['char_infos']) < 8, list(books.keys())))
    keys = list(filter(lambda k: len(books[k]['summary'].split()) < 800, keys))
    excludes = [
        ('The Maltese Falcon', 'shmoop'),
        ('East of Eden', 'shmoop'),
        ('The Threepenny Opera', 'shmoop'),
        ("Salem's Lot", 'shmoop'),
        ('Othello', 'cliffnotes'),
    ]
    keys = set(keys) - set(excludes)
    selected_keys = random.sample(keys, 20)
    selected_books = [generate_human_eval_data(books[key], list(char_names)) for key in selected_keys]
    export_dataset_to_csv(human_eval_data_filename, selected_books)

    # counter = {}
    # metadata = []
    # for book in books.values():
    #     num_chars = len(book['char_infos'])
    #     metadata.append(num_chars)
    #     counter[num_chars] = counter.get(num_chars, 0) + 1
    
    # keys = sorted(list(counter.keys()))
    # print(f'total: {len(books)} books')
    # for key in keys:
    #     print(f'{key} characters: {counter[key]} books')

    # print(f'median: {np.median(metadata)}')
    # print(f'mean: {np.mean(metadata)}')
    

    # # print(list(books.keys())[:10])
    # fills = books[('Agamemnon, The Choephori, and The Eumenides', 'cliffnotes')]

    # templateLoader = jinja2.FileSystemLoader(searchpath="./")
    # templateEnv = jinja2.Environment(loader=templateLoader)
    # TEMPLATE_FILE = "html_template/final_AMT.html"
    # template = templateEnv.get_template(TEMPLATE_FILE)
    # html = template.render(**fills)
    # with open('htmls/test.html', 'w') as out_f:
    #     out_f.write(html)

def main():
    data = load_dataset_from_jsonl(untruncated_masked_character_dataset_filter_by_name_and_desc_filename)
    model_results = load_dataset_from_jsonl('test_prediction_beams5_maxlen_1024.jsonl')
    # d = data[0]
    # print(d['character_name'])
    # print(d['multichoice'].values())

    # aggregate by book
    books = {}
    char_names = set()
    for d in data:
        key = (d['book_title'], d['source'])
        l = books.get(key, {
            'book_title': d['book_title'],
            'source': d['source'],
            'summary': d['summary'],
            'char_infos': [],
        })
        l['char_infos'].append({
            'character_name': d['character_name'],
            'description': d['description'],
            'masked_description': d['masked_description'].replace('[MASK]', '&#8287;&#8287;______&#8287;&#8287;'),
        })
        char_names.add(d['character_name'])
        books[key] = l

    # num_words = list(map(lambda b: len(b['summary'].split()), books.values()))
    # print(sum(num_words) / len(num_words))

    keys = list(filter(lambda k: 4 < len(books[k]['char_infos']) < 8, list(books.keys())))
    keys = list(filter(lambda k: len(books[k]['summary'].split()) < 800, keys))
    excludes = [
        ('The Maltese Falcon', 'shmoop'),
        ('East of Eden', 'shmoop'),
        ('The Threepenny Opera', 'shmoop'),
        ("Salem's Lot", 'shmoop'),
        ('Othello', 'cliffnotes'),
    ]
    keys = set(keys) - set(excludes)
    selected_keys = random.sample(keys, 20)
    selected_books = [generate_human_eval_data(books[key], list(char_names)) for key in selected_keys]
    export_dataset_to_csv(human_eval_data_filename, selected_books)

if __name__ == '__main__':
    main()
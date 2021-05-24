import ast
from dataclasses import dataclass
from final_process.text_diff_tool import TextDiffTool
import os

from final_process.database_util import CharacterInfoWithMaskedDescription, DatabaseConnection
from final_process.book_char_dataset import BasicBookCharDataset, FinalBookCharDataset
from final_process.key_translator import KeyTranslator
from final_process.common_util import read_json

_ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
_STATIC_DIR = os.path.join(_ROOT_DIR, 'static')
_DATA_DIR = os.path.join(_ROOT_DIR, 'final_data')

# filenames
LIST_CHAR_KEYS_FILENAME = os.path.join(_STATIC_DIR, 'list_char_keys.json')
DESCRIPTION_CHANGES_FILENAME = (
    os.path.join(_STATIC_DIR, 'description_changes.json')
)
MASKED_DESCRIPTION_CHANGES_FILENAME = (
    os.path.join(_STATIC_DIR, 'masked_description_changes.json')
)
DATASET_OUTPUT_FILENAME = os.path.join(_DATA_DIR, 'data.jsonl')


KEY_TRANSLATOR = KeyTranslator.load_from_json_files(
    os.path.join(_STATIC_DIR, 'new_book_key_to_old_book_key_mapping.json'),
    os.path.join(_STATIC_DIR, 'old_book_key_to_new_book_key_mapping.json'),
    os.path.join(_STATIC_DIR, 'new_char_key_to_old_char_key_mapping.json'),
    os.path.join(_STATIC_DIR, 'old_char_key_to_new_char_key_mapping.json'),
)

def pre_clean_description(description, char_key):
    while description.endswith(' Read an'):
        description = description[:-8]
    
    description = description.replace(
        'M&amp;Ms; or peanut',
        'M&amp;Ms or peanut',
    )

    if char_key == ('Walden', 'shmoop', 'Thoreau'):
        description = description[245:] + description[:245]
    
    return description

def main():
    db_conn = DatabaseConnection('lcdata-wayback')
    dataset = BasicBookCharDataset.load_from_database(db_conn)

    dataset.replace_keys(
        KEY_TRANSLATOR.new_to_old_book_key_mapping,
        KEY_TRANSLATOR.new_to_old_char_key_mapping,
    )

    list_char_keys = read_json(LIST_CHAR_KEYS_FILENAME)
    char_keys = [ast.literal_eval(char_key) for char_key in list_char_keys]
    dataset.filter_by_char_keys(char_keys)

    for char_key, char_info in dataset.char_lookup.items():
        char_info.description = pre_clean_description(
            char_info.description, char_key
        )

    description_changes = read_json(DESCRIPTION_CHANGES_FILENAME)
    change_lookup = {
        ast.literal_eval(key): val
        for key, val in description_changes.items()
    }
    dataset.adjust_description(change_lookup)

    masked_description_changes = read_json(MASKED_DESCRIPTION_CHANGES_FILENAME)
    masked_change_lookup = {
        ast.literal_eval(key): val
        for key, val in masked_description_changes.items()
    }
    new_char_infos = []
    for char_key, char_info in dataset.char_lookup.items():
        changes = masked_change_lookup[char_key]
        masked_description = ' '.join(
            TextDiffTool.restore_list_from_text(
                char_info.description, changes
            )
        )
        new_char_info = (
            CharacterInfoWithMaskedDescription
                .generate_from_char_info(char_info, masked_description)
        )
        new_char_infos.append(new_char_info)
    final_dataset = FinalBookCharDataset(
        books=list(dataset.book_lookup.values()),
        characters=new_char_infos,
    )

    final_dataset.export_to_jsonl(DATASET_OUTPUT_FILENAME)

if __name__ == '__main__':
    main()
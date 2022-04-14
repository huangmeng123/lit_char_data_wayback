import ast
import configparser
from typing import final
from lib.text_diff_tool import TextDiffTool
import os

from lib.database_util import CharacterInfoWithMaskedDescription, DatabaseConnection
from lib.book_char_dataset import BasicBookCharDataset, FinalBookCharDataset
from lib.key_translator import KeyTranslator
from lib.common_util import read_json

_ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
_STATIC_DIR = os.path.join(_ROOT_DIR, 'static')

# filenames
RUNTIME_CONFIG_FILENAME = os.path.join(_ROOT_DIR, 'runtime.ini')
LIST_CHAR_KEYS_FILENAME = os.path.join(_STATIC_DIR, 'list_char_keys.json')
DESCRIPTION_CHANGES_FILENAME = (
    os.path.join(_STATIC_DIR, 'description_changes.json')
)
SUMMARY_CHANGES_FILENAME = (
    os.path.join(_STATIC_DIR, 'summary_changes.json')
)
MASKED_DESCRIPTION_CHANGES_FILENAME = (
    os.path.join(_STATIC_DIR, 'masked_description_changes.json')
)

TRAIN_KEY_ORDER_FILENAME = os.path.join(_STATIC_DIR, 'train_keys.txt')
TEST_KEY_ORDER_FILENAME = os.path.join(_STATIC_DIR, 'test_keys.txt')
VAL_KEY_ORDER_FILENAME = os.path.join(_STATIC_DIR, 'val_keys.txt')

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

def load_config():
    config = configparser.ConfigParser()
    config.read(RUNTIME_CONFIG_FILENAME)
    return config

def main():
    config = load_config()
    db_conn = DatabaseConnection(
        host=config['database']['host'],
        user=config['database']['user'],
        password=config['database']['password'],
        dbname=config['database']['dbname'],
    )
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

    summary_changes = read_json(SUMMARY_CHANGES_FILENAME)
    change_lookup = {
        ast.literal_eval(key): val
        for key, val in summary_changes.items()
    }
    dataset.adjust_summary(change_lookup)

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

    final_dataset.export_to_jsonl(config['output']['filename'])

    with open(TRAIN_KEY_ORDER_FILENAME) as train_key_f:
        train_keys = list(train_key_f.readlines())
        final_dataset.export_to_jsonl_with_selected_keys(
            config['output']['train_filename'], train_keys)

    with open(TEST_KEY_ORDER_FILENAME) as test_key_f:
        test_keys = list(test_key_f.readlines())
        final_dataset.export_to_jsonl_with_selected_keys(
            config['output']['test_filename'], test_keys)

    with open(VAL_KEY_ORDER_FILENAME) as val_key_f:
        val_keys = list(val_key_f.readlines())
        final_dataset.export_to_jsonl_with_selected_keys(
            config['output']['val_filename'], val_keys)
    
if __name__ == '__main__':
    main()
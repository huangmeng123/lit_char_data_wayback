from data_center import DataCenter
from data_center_coref import CorefDataCenter

def coref():
    filename = '../data/short-desc-summeries-spanbert-base-400.out'
    coref_dc = CorefDataCenter.build_from_raw_file(filename)
    print(coref_dc.get_token_based_references(1))

def original():
    filename = '../data/original-book-export-from-database.json'
    dc = DataCenter()
    dc.export_to_file(filename)
    dc = DataCenter.build_from_file(filename)
    for sentence in dc.get_sentence_based_summary(1):
        print(sentence)


def main():
    original()

if __name__ == '__main__':
    main()
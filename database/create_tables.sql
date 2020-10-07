CREATE TABLE literatures (
    book_title TEXT,
    source TEXT,
    book_url TEXT,
    author TEXT,
    summary_url TEXT,
    summary_text TEXT,
    character_list_url TEXT,
    PRIMARY KEY (book_title, source)
);

CREATE TABLE characters (
    character_name TEXT,
    book_title TEXT,
    source TEXT,
    character_list_url TEXT,
    character_order INT,
    description_url TEXT,
    description_text TEXT,
    analysis_url TEXT,
    analysis_text TEXT,
    PRIMARY KEY (character_name, book_title, source),
    FOREIGN KEY (book_title, source)
        REFERENCES literatures (book_title, source) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION
);
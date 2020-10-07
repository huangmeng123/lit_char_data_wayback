# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field

# LiteratureInfo stores a single online literature's information scraped
#   by the scrapy 
class LiteratureInfo(Item):
    # primary keys
    book_title = Field() # required
    source = Field() # required
    
    # general info
    book_url = Field() # optional
    author = Field() # optional

    # summary info
    summary_url = Field() # optional
    summary_text = Field() # optional

    # character list info
    character_list_url = Field() # unique or null if no character list


# CharacterInfo stores a single character's information from a book of
#   a online source scraped by the scrapy
class CharacterInfo(Item):
    # primary keys
    character_name = Field() # required
    book_title = Field() # required
    source = Field()

    # character list info
    character_list_url = Field() # same field in LiteratureInfo
    character_order = Field() # order of the importance of character

    # character description info
    description_url = Field() # optional; null if no description
    description_text = Field() # optional; null if no description

    # character analysis info
    analysis_url = Field() # optional; null if no analysis
    analysis_text = Field() # optional; null if no analysis
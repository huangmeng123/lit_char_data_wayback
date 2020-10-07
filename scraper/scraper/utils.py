# -*- coding: utf-8 -*-
"""Utility functions for scrapynotes project"""

import re


def extract_paragraphs(paragraphs):
    """
    Extract text elements from a list of Selector nodes and return a newline separated
    set of lines where each line consists of text with only space(" ") as delimiter.
    """
    return "\n".join((extract_text(para) for para in paragraphs))


def extract_text(node, use_selector=True):
    """
    Extract all text elements inside a Selector node using `.css('::text').getall()` and
    remove all extraneous whitespaces including newlines/tabs/non-breaking-whitespace
    etc. Then return a string containing the text with only space(" ") as delimiter.

    If `use_selector=False` then a direct `.getall()` is invoked and `.css('::text')` is
    skipped. This is useful when the selected node is of type `foo.xpath('./../text()')`
    and as such already provides a set of text nodes.
    """

    def token_generator(node):
        if use_selector:
            node = node.xpath("./text()")
        for text in node.getall():
            yield from text.split()

    return " ".join(token_generator(node))

def remove_html_tags(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext
"""
Filter low quality fill-blank data using regex patterns
"""

import re
import json
import os
from typing import Tuple

def is_date_format(text: str) -> bool:
    """
    Check if the text matches any date format
    
    Args:
        text: text to check
        
    Returns:
        bool: True if text matches a date pattern, False otherwise
    """
    date_patterns = [
        r'^(\d{4}年\d{1,2}月\d{1,2}日)$',  # yyyy年mm月dd日
        r'^(\d{1,2}月\d{1,2}日)$',         # mm月dd日
        r'^(?i)(January|February|March|April|May|June|July|August|September|October|November|December)\s\d{1,2},\s\d{4}$',  # Month dd, yyyy
        r'^(?i)(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s\d{1,2},\s\d{4}$',  # Abbreviated month dd, yyyy
        r'^(?i)(January|February|March|April|May|June|July|August|September|October|November|December)\s\d{1,2}(st|nd|rd|th)?$',  # Month dd[th]
        r'^(?i)(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s\d{1,2}(st|nd|rd|th)?$',  # Abbreviated month dd[th]
    ]
    
    for pattern in date_patterns:
        if re.match(pattern, text):
            return True
    return False

def is_figure_or_table_reference(text: str) -> bool:
    """
    Check if the text is a figure or table reference
    
    Args:
        text: text to check
        
    Returns:
        bool: True if text is a figure or table reference, False otherwise
    """
    # I, II, III, IV, V, etc.
    roman_pattern = r'(?:Ⅰ|Ⅱ|Ⅲ|Ⅳ|Ⅴ|Ⅵ|Ⅶ|Ⅷ|Ⅸ|Ⅹ|Ⅺ|Ⅻ|I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)'
    
    # re.match: match from the beginning of the text
    match_patterns = [
        # Figure references
        r'^(?i)Figure\s*(\d+|' + roman_pattern + r').*$',     # Figure x...
        r'^(?i)Figures\s*(\d+|' + roman_pattern + r').*$',    # Figures x...
        r'^(?i)Figure[.]\s*(\d+|' + roman_pattern + r').*$',  # Figure.x...
        r'^(?i)Figures[.]\s*(\d+|' + roman_pattern + r').*$', # Figures.x...
        
        # Chinese figure references
        r'^图\s*(\d+|' + roman_pattern + r').*$',             # 图x...
        r'^图\s*([a-z]).*$',                                  # 图[]... ([] is a letter)
        
        # Table references
        r'^表\s*(\d+|' + roman_pattern + r').*$',             # 表x...
        r'^(?i)Table\s*(\d+|' + roman_pattern + r').*$',      # Table x...
        r'^(?i)Tables\s*(\d+|' + roman_pattern + r').*$',     # Tables x...
    ]

    # re.search: search the whole text
    # \b is word boundary, ensure the match is a complete word, e.g. match "figure" instead of "configure"
    search_patterns = [
        r'(?i)fig\.',               # fig.
        r'(?i)the figure',          # the figure
        r'(?i)this figure',         # this figure
        r'\b(?i)figures?\b',          # figure, figures 

        r'(?i)the table',           # the table
        r'(?i)this table',          # this table
        r'\b(?i)tables?\b',           # table, tables 
    ]
    
    for pattern in match_patterns:
        if re.match(pattern, text):
            return True
    
    for pattern in search_patterns:
        if re.search(pattern, text):
            return True
    return False

def is_other_to_be_filtered(text: str) -> bool:
    patterns = [
        r'(?i)the study',           # the study
        r'(?i)本研究',              # 本研究
        r'(?i)本实验',              # 本实验

        r'\$',                      # "$"
    ]
    
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    return False

def answer_filter(answer: str) -> bool:
    if is_date_format(answer) or is_figure_or_table_reference(answer) or is_other_to_be_filtered(answer):
        return True
    return False

def question_filter(question: str, answer: str) -> bool:
    def is_answer_in_question(question: str, answer: str) -> bool:
        return answer.lower() in question.lower()

    if is_figure_or_table_reference(question) or is_other_to_be_filtered(question) or is_answer_in_question(question, answer):
        return True
    return False

def filter_by_regex(origin_data_path: str, filtered_data_path: str, noisy_data_path: str) -> Tuple[int, int]:
    """
    Filter low quality fill-blank data based on regex patterns
    
    Args:
        origin_data_path: path to the original data file
        filtered_data_path: path to save the filtered data
        noisy_data_path: path to save the noisy data 
        
    Returns:
        Tuple[int, int]: (number of remaining items, number of filtered out items)
    """
    # Ensure output directories exist
    os.makedirs(os.path.dirname(filtered_data_path), exist_ok=True)
    os.makedirs(os.path.dirname(noisy_data_path), exist_ok=True)
    
    with open(origin_data_path, "r", encoding="utf-8") as f:
        data = json.load(f) # dict

    remain_data = {}
    noisy_data = {}
    
    for key, values in data.items():
        values.pop("masked_node_type", None)
        values.pop("loss", None)
        
        answer = values['answer'].strip()
        question = values['question'].strip()
        if answer_filter(answer) or question_filter(question, answer):
            noisy_data[key] = values
        else:
            remain_data[key] = values
    
    with open(filtered_data_path, "w", encoding="utf-8") as f:
        json.dump(remain_data, f, ensure_ascii=False, indent=4)
    
    with open(noisy_data_path, "w", encoding="utf-8") as f:
        json.dump(noisy_data, f, ensure_ascii=False, indent=4)
    
    remain_count = len(remain_data)
    noisy_count = len(noisy_data)
    
    return remain_count, noisy_count

if __name__ == "__main__":
    import logging
    
    # Configure logging for standalone usage
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    origin_file = ""
    filtered_data_path = ""
    noisy_output = ""
    
    logger.info(f"Starting regex-based filtering...")
    logger.info(f"Input file: {origin_file}")
    logger.info(f"Output filtered file: {filtered_data_path}")
    logger.info(f"Output noisy file: {noisy_output}")
    
    remain_count, noisy_count = filter_by_regex(origin_file, filtered_data_path, noisy_output)
    total_count = remain_count + noisy_count
    
    logger.info(f"Regex filtering completed:")
    logger.info(f"  Total items: {total_count}")
    logger.info(f"  Remaining items: {remain_count}")
    logger.info(f"  Filtered out items: {noisy_count}")
    logger.info(f"  Filter rate: {noisy_count/total_count*100:.2f}%")


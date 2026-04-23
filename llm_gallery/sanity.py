from __future__ import annotations

import re
from collections import Counter


WORD_RE = re.compile(r"[A-Za-z0-9']+")


def output_is_sane(text: str) -> bool:
    sample = text.strip()
    if not sample:
        return False
    if not any(character.isalnum() for character in sample):
        return False
    if len(sample) >= 8 and len(set(sample)) <= 2:
        return False
    if re.search(r"(.)\1{7,}", sample):
        return False

    tokens = WORD_RE.findall(sample.lower())
    if not tokens:
        return False
    if len(tokens) >= 8:
        most_common_count = Counter(tokens).most_common(1)[0][1]
        if most_common_count / len(tokens) > 0.6:
            return False

    alnum_count = sum(character.isalnum() for character in sample)
    punctuation_count = sum(
        not character.isalnum() and not character.isspace() for character in sample
    )
    if punctuation_count > alnum_count and alnum_count < 8:
        return False
    return True

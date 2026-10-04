import re


def preprocess_disease_name(name: str) -> str:
    """
    Basic normalization of user-provided disease text.

    This function intentionally does NOT perform semantic
    normalization. It only cleans the input.
    """

    if not isinstance(name, str):
        raise TypeError("Disease name must be a string.")

    name = name.strip()

    # Collapse repeated whitespace
    name = re.sub(r"\s+", " ", name)

    # Lowercase for matching
    name = name.lower()

    return name

def normalize_for_matching(text: str) -> str:
    """
    Creates a comparison representation.

    We retain the original text elsewhere.
    """

    text = text.lower().strip()

    # Normalize common punctuation
    text = text.replace("-", " ")
    text = text.replace("_", " ")

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    return text
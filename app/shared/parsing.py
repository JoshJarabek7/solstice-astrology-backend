import re


def parse_mentions(text: str) -> list[str]:
    """Extracts all mentions in the text.

    A mention is defined as a string that starts with '@' followed by alphanumeric
    characters and underscores.

    Args:
        text (str): The text to parse.

    Returns:
        List[str]: A list of mentions found in the text.
    """
    return re.findall(r"@(\w+)", text)


def parse_hashtags(text: str) -> list[str]:
    """Extracts all hashtags in the text.

    A hashtag is defined as a string that starts with '#' followed by alphanumeric
    characters and underscores.

    Args:
        text (str): The text to parse.

    Returns:
        List[str]: A list of hashtags found in the text.
    """
    return re.findall(r"#(\w+)", text)

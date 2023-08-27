import re


def is_uuid_format(value: str) -> bool:
    uuid_pattern = re.compile(
        r"^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$"
    )
    return bool(uuid_pattern.match(value))

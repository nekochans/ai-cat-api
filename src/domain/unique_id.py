import uuid
import re


def is_uuid_v4_format(uuid_str: str) -> bool:
    try:
        uuid_object = uuid.UUID(uuid_str, version=4)
    except ValueError:
        return False

    return (
        uuid_object.version == 4
        and re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            uuid_str,
        )
        is not None
    )

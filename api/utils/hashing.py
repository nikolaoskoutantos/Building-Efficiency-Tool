import hashlib
import json
from typing import Any

def hash_object(obj: Any, algorithm: str = "sha256") -> str:
    """
    Hash any serializable Python object (e.g., API response) using the specified algorithm.
    Returns the hex digest string.
    """
    # Convert the object to a canonical JSON string
    obj_str = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    h = hashlib.new(algorithm)
    h.update(obj_str.encode("utf-8"))
    return h.hexdigest()

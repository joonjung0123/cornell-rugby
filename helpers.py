import json
import os
import tempfile

def load_json(path):
    """Load a JSON file and return its contents as a Python object.
    Returns an empty list if the file does not exist."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    """Atomically write data as JSON to path.
    Writes to a temp file first, then renames to avoid corruption."""
    dir_name = os.path.dirname(path) or "."
    os.makedirs(dir_name, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    except Exception:
        os.unlink(tmp_path)
        raise


if __name__ == "__main__":
    # Smoke test
    test_path = "data/men/players.json"
    data = load_json(test_path)
    print(f"Loaded {len(data)} players from {test_path}")
    print(json.dumps(data[:1], indent=2))

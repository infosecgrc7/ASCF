"""Deterministic data I/O and source fingerprints."""
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import unicodedata

class DataError(ValueError):
    pass

def load(path):
    with Path(path).open(encoding='utf-8-sig') as stream:
        return json.load(stream, parse_constant=lambda value: (_ for _ in ()).throw(DataError('Non-finite JSON number: ' + value)))

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_json(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    handle, temporary = tempfile.mkstemp(prefix=target.name + '.', suffix='.tmp', dir=target.parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def key(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().replace('µ', 'μ').split())

def score(value):
    if isinstance(value, bool) or value is None:
        raise DataError('Strength must be a finite number, not boolean/null')
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise DataError('Strength must be numeric') from None
    if not math.isfinite(result) or not 1 <= result <= 10:
        raise DataError('Strength must be finite and in 1–10')
    return int(result) if result.is_integer() else result

def text(value):
    return isinstance(value, str) and bool(value.strip())

def unique(items, label):
    if len(set(items)) != len(items):
        raise DataError('Duplicate ' + label)

def require(condition, message):
    if not condition:
        raise DataError(message)

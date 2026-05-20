"""Value generation and mutation for fuzzing."""
import json
import os
import random
import string

from pyradamsa import pyradamsa

_FUZZDB_PATH = os.path.join(os.path.dirname(__file__), "fuzzdb", "attack", "all-attacks", "all-attacks-unix.txt")
_ATTACK_LINES = None


def _attack_lines():
    global _ATTACK_LINES
    if _ATTACK_LINES is None:
        try:
            with open(_FUZZDB_PATH, encoding="utf-8", errors="replace") as f:
                _ATTACK_LINES = f.read().splitlines()
        except OSError:
            _ATTACK_LINES = []
    return _ATTACK_LINES


def generation(value_type):
    """Generate a random value of the given type ('int', 'str', 'float', 'bool')."""
    max_rand = 999 ** 9
    lines = _attack_lines()
    if lines and random.randint(0, 1) and random.randint(0, 1):
        return random.choice(lines)

    if value_type == "int":
        return random.randrange(0, random.randrange(1, max_rand))

    if value_type == "str":
        charset = random.choice([
            string.printable, string.ascii_lowercase, string.ascii_uppercase,
            string.ascii_letters, string.digits, string.hexdigits,
        ])
        lengths = [i + 2 for i in range(100)] + [i + 10 for i in range(100)] + [999 ** 2]
        length = random.randrange(0, random.randrange(1, random.choice(lengths)))
        return "".join(random.choices(charset, k=length))

    if value_type == "float":
        v1 = random.randrange(0, random.randrange(1, max_rand))
        v2 = int(str(random.randrange(0, random.randrange(1, max_rand)))[0:random.randrange(1, 10)])
        return float("%d.%d" % (v1, v2))

    if value_type == "bool":
        return bool(random.randint(0, 1))

    return None


def key_generation(dictionary):
    """Replace 'fuzz<type>' placeholders with generated values."""
    s = json.dumps(dictionary)
    while "fuzz" in s:
        start_id = s.find("fuzz")
        # Find the closing quote of the placeholder value (e.g. "fuzzint" -> after "int")
        end_id = s.find('"', start_id + 1)
        if end_id == -1:
            break
        value = s[start_id - 1:end_id + 1]
        try:
            value_type = value.split("fuzz")[1].replace('"', "")
        except IndexError:
            break
        s = s.replace(value, json.dumps(generation(value_type)), 1)
    try:
        return json.loads(s)
    except json.decoder.JSONDecodeError:
        return dictionary


def mutation(value):
    """Mutate a string value using Radamsa."""
    rad = pyradamsa.Radamsa()
    mutated = rad.fuzz(str(value).encode())
    try:
        return mutated.decode()
    except UnicodeDecodeError:
        return value


def dict_mutation(dictionary, max_attempts=100):
    """Mutate the entire JSON or just its 'params' field."""
    for _ in range(max_attempts):
        try:
            if random.randint(0, 1):
                return json.loads(mutation(json.dumps(dictionary)))
            params = dictionary.get("params")
            if isinstance(params, dict):
                result = dict(dictionary)
                result["params"] = json.loads(mutation(json.dumps(params)))
                return result
            return dictionary
        except Exception:
            continue
    return dictionary


def _recurs_list(lst):
    result = list(lst)
    for i in range(len(result)):
        if isinstance(result[i], dict):
            result[i] = _recurs_dict(result[i])
        elif isinstance(result[i], list):
            result[i] = _recurs_list(result[i])
        else:
            result[i] = mutation(str(result[i]))
    return result


def _recurs_dict(dictionary):
    dictionary = dict(dictionary)
    random_key = random.choice(list(dictionary.keys()))
    value = dictionary[random_key]
    if isinstance(value, dict):
        dictionary[random_key] = _recurs_dict(value)
    elif isinstance(value, list):
        dictionary[random_key] = _recurs_list(value)
    else:
        dictionary[random_key] = mutation(str(value))
    return dictionary


def key_mutation(dictionary):
    """Mutate values for random key(s) in 'params'."""
    dictionary = dict(dictionary)
    params = dictionary.get("params")
    if isinstance(params, dict):
        for _ in range(random.randint(1, 10)):
            params = _recurs_dict(params)
        dictionary["params"] = params
    elif isinstance(params, list):
        params = list(params)
        if params:
            for i in range(len(params)):
                if random.randint(0, 1):
                    params[i] = mutation(str(params[i]))
        else:
            for i in range(random.randint(1, 100)):
                params.append(mutation(str(i)))
        dictionary["params"] = params
    elif params is not None:
        dictionary["params"] = mutation(str(params))
    return dictionary

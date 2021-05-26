from typing import List, Any

import json

def read_jsonl(filename: str) -> List[Any]:
    data: List[Any] = []
    with open(filename) as in_f:
        for line in in_f.readlines():
            data.append(json.loads(line))
    return data

def write_jsonl(filename: str, data: List[Any]):
    with open(filename, 'w') as out_f:
        for d in data:
            out_f.write(json.dumps(d)+'\n')

def read_json(filename: str) -> Any:
    with open(filename) as in_f:
        return json.load(in_f)
#!/usr/bin/env python3
"""Generates the long-context refactor prompt (real-task ~60K benchmark).

Adapted from Qwen3.8-vLLM-KVarN-MTP-Arc-Experiments (scripts/generate_messy.py +
build_prompt.py). Deterministic: seed 42, so every run/regeneration reproduces the
same prompt text (79 repeats ~ 60K tokens on the Qwen tokenizer family; recorded
token counts still vary slightly across models/tokenizers).

Outputs (into --out-dir, default <tmp>/llm-bench-prompts - a scratch dir, never the
repo working tree):
  full_prompt.txt                  - instruction wrapper + near-repetitive legacy code
                                     (the prompt text)
  prompt-long-context-35b.json     - raw /v1/completions payload, 35B family
  prompt-long-context-flash.json   - raw /v1/completions payload, Flash-Next

Flags:
  --repeats N     entity-template repeats (default 79, ~60K tokens)
  --out-dir DIR   output directory (default <tmp>/llm-bench-prompts, a scratch dir)

Payloads carry the prompt + request shape only (n_predict 512, cache_prompt false,
ignore_eos true - the unified timing protocol, see methodology.md/test-prompts.md) -
no sampling parameters: the served config decides sampling. Only speed is measured
with this prompt - no output-quality evaluation passes.
"""

import argparse
import json
import os
import random
import sys
import tempfile

random.seed(42)

ENTITIES = [
    "user",
    "order",
    "product",
    "invoice",
    "customer",
    "shipment",
    "employee",
    "ticket",
    "payment",
    "account",
    "vendor",
    "warehouse",
    "review",
    "coupon",
    "subscription",
    "session",
    "device",
    "report",
    "category",
    "transaction",
]

INSTRUCTION_PREFIX = """You are reviewing a legacy Python codebase full of common beginner mistakes.
Refactor the following script to use modern, idiomatic Python practices. Specifically fix:
- Global mutable state and bare `except` clauses
- Mutable default arguments (e.g. `def f(x=[])`)
- Manual index loops (`for i in range(len(x))`) instead of iteration/enumerate
- `== None` / `== True` comparisons instead of `is None` / truthiness
- String concatenation instead of f-strings
- Inconsistent naming conventions (mixed camelCase/snake_case/PascalCase)
- Missing type hints and docstrings
- Massive code duplication (near-identical functions that should be parameterized)
- Manual file open/close instead of context managers

Produce a cleaned-up, well-structured version. Explain your key changes briefly at the end.

```python
"""

INSTRUCTION_SUFFIX = "\n```\n"

HEADER = """import os,sys,json,time,random,math,re,datetime
data = []
DATA2 = {}
temp = None
counter = 0
GLOBAL_CACHE = {}
errors_list = []

def log(msg):
    print("LOG: " + str(msg))

def readFile(fn):
    f = open(fn, "r")
    d = f.read()
    return d

def writeFile(fn, content):
    f = open(fn, "w")
    f.write(content)
    f.close()

class dataManager:
    def __init__(self):
        self.items = []
        self.Items2 = []
        self.count = 0
    def AddItem(self, x):
        self.items.append(x)
        self.count = self.count + 1
        return None
    def getItems(self):
        return self.items
    def process(self, l=[]):
        for i in range(len(l)):
            l[i] = l[i] * 2
        return l

"""

FUNC_TEMPLATE = """
def process_{entity}_{idx}(data_{idx}=[]):
    global counter
    result = []
    for i in range(len(data_{idx})):
        item = data_{idx}[i]
        if item == None:
            continue
        try:
            if item['status'] == "active" or item['status'] == "Active" or item['status'] == "ACTIVE":
                x = item['value'] * {mult}
                y = x + {add}
                z = y / {div} if {div} != 0 else 0
                temp_result = str(item['id']) + "_" + str(z)
                result.append(temp_result)
                counter = counter + 1
            else:
                if item.has_key('legacy_status') if hasattr(item, 'has_key') else 'legacy_status' in item:
                    result.append(item['legacy_status'])
        except:
            errors_list.append("error processing {entity} " + str(i))
            pass
    output_{idx} = []
    for j in range(0, len(result)):
        output_{idx}.append(result[j])
    return output_{idx}

def validate_{entity}_{idx}(rec):
    if rec == None:
        return False
    if rec.get('name') == "" or rec.get('name') == None:
        return False
    if len(rec.get('name')) < 1:
        return False
    l = len(rec.get('email', ''))
    if l == 0:
        return False
    ok = True
    if '@' not in rec.get('email',''):
        ok = False
    return ok

def calculate_{entity}_total_{idx}(items):
    total = 0
    for i in range(len(items)):
        total = total + items[i]['price'] * items[i]['qty']
    tax = total * 0.{taxrate}
    grand_total = total+tax
    return grand_total

def format_{entity}_name_{idx}(first, last):
    fullname = first + " " + last
    return fullname.upper() if {upper_flag} else fullname.lower()

def get_{entity}_by_id_{idx}(id, lst):
    for x in lst:
        if x['id']==id:
            return x
    return None

def update_{entity}_{idx}(obj, newData):
    for k in newData.keys():
        obj[k] = newData[k]
    GLOBAL_CACHE[obj.get('id', {idx})] = obj
    return obj

def delete_{entity}_{idx}(lst, id):
    newList = []
    for i in lst:
        if i['id'] != id:
            newList.append(i)
    return newList

class {Entity}Handler{idx}:
    def __init__(self, name, value = []):
        self.name = name
        self.value = value
        self.Data = {{}}
        self.isActive = True
    def DoStuff(self):
        r = []
        for i in range(len(self.value)):
            if self.value[i] % 2 == 0:
                r.append(self.value[i])
        return r
    def check(self):
        if self.isActive == True:
            return True
        else:
            return False
    def to_string(self):
        s = ""
        for k in self.Data:
            s = s + str(k) + "=" + str(self.Data[k]) + ","
        return s

"""

FOOTER = """
def main():
    print("starting")
    d = dataManager()
    for i in range(10):
        d.AddItem(i)
    print(d.getItems())
    log("done")

if __name__=="__main__":
    main()
"""


def build_long_context_code(target_repeats):
    parts = [HEADER]
    for idx in range(target_repeats):
        entity = ENTITIES[idx % len(ENTITIES)]
        parts.append(
            FUNC_TEMPLATE.format(
                entity=entity,
                Entity=entity.capitalize(),
                idx=idx,
                mult=random.randint(2, 9),
                add=random.randint(1, 50),
                div=random.randint(1, 7),
                taxrate=random.randint(5, 25),
                upper_flag=random.choice(["True", "False"]),
            )
        )
    parts.append(FOOTER)
    return "".join(parts)


def build_prompt(target_repeats):
    return (
        INSTRUCTION_PREFIX
        + build_long_context_code(target_repeats)
        + INSTRUCTION_SUFFIX
    )


def request_shape():
    # Unified timing protocol (see methodology.md / test-prompts.md): raw /v1/completions,
    # n_predict 512, cache_prompt false, ignore_eos true. ignore_eos keeps every pass at a
    # full 512-token decode window; without it qwen4exp (Flash-Next) stops after 1 token on
    # this prompt and the 35B moe-cache fork does so rarely (issues.md).
    return {"n_predict": 512, "cache_prompt": False, "ignore_eos": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--repeats",
        type=int,
        default=79,
        help="entity-template repeats (79 ~ 60K tokens; 153 was the retired ~116K prompt)",
    )
    ap.add_argument(
        "--out-dir",
        default=os.path.join(tempfile.gettempdir(), "llm-bench-prompts"),
        help="output directory (default: <tmp>/llm-bench-prompts - never the repo)",
    )
    args = ap.parse_args()

    out_dir = os.path.expanduser(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    prompt = build_prompt(args.repeats)

    with open(os.path.join(out_dir, "full_prompt.txt"), "w") as f:
        f.write(prompt)

    for family in ("35b", "flash"):
        payload: dict = {"prompt": prompt}
        payload.update(request_shape())
        name = f"prompt-long-context-{family}.json"
        with open(os.path.join(out_dir, name), "w") as f:
            json.dump(payload, f)

    print(
        f"wrote full_prompt.txt ({len(prompt)} chars) + 2 payload JSONs "
        f"(prompt + request shape only) to {out_dir}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()

# Reforcer – one-shot Text-to-SQL with ReFoRCE + OpenAI

> **Fork origin:** <https://github.com/Snowflake-Labs/ReFoRCE>  
> **Extra goodies in this fork**
> - `methods/ReFoRCE/api.py` → single-call Python wrapper  
> - `demo.py` → zero-config smoke test (creates a sample SQLite DB, asks a question, prints SQL + result)  
> - Thin **requirements** file so a fresh env works first try  
> - README you’re reading now

---

## 1 Quick start (local)

```bash
# clone
git clone https://github.com/Hajiyevrehman/Reforcer.git
cd Reforcer

# create fresh env (conda OR python -m venv)
conda create -n reforce310 python=3.10 -y        # ⇐ need 3.10+ because of |-type hints
conda activate reforce310

# install deps
pip install -r methods/ReFoRCE/requirements.txt

# put your key in env
export OPENAI_API_KEY="sk-…"

# run the smoke-test
python demo.py
```

You should see something like

```text
local-1234abcd
…/log.log: chat_session len: …
SQL:
 SELECT name FROM products;

Answer:
     name
0   Apple
1  Banana
2   Chair
```

---

## 2 Using the wrapper in your own code

```python
from methods.ReFoRCE.api import query_one
import pathlib, sqlite3

db = pathlib.Path("shop.sqlite")
with sqlite3.connect(db) as con:
    con.executescript("""
        CREATE TABLE IF NOT EXISTS orders(id INT, total REAL);
        INSERT OR IGNORE INTO orders VALUES (1, 42.5), (2, 30.0);
    """)

res = query_one(
    sqlite_path = db,
    question    = "What is the average order total?",
    model       = "gpt-4o",        # any chat-completion model id
    num_workers = 2,               # forwarded to run.py
    extra_schema= "-- sales are in USD"  # optional human notes
)

print("SQL:", res["sql"])
print(res["answer"])
```

Returned dict keys

| key       | type              | description                           |
|-----------|-------------------|---------------------------------------|
| `sql`     | `str`             | model-generated SQL                   |
| `answer`  | `pandas.DataFrame`| execution result (first 1000 rows)    |
| `log`     | `pathlib.Path`    | full ReFoRCE log for this run         |
| `workdir` | `pathlib.Path`    | temp folder with db-copy + outputs    |

---

## 3 Google Colab mini-demo

```python
!git clone https://github.com/Hajiyevrehman/Reforcer.git -q
%cd Reforcer
!pip install -q -r methods/ReFoRCE/requirements.txt# Colab pin

import os, sqlite3, pathlib
os.environ["OPENAI_API_KEY"] = "sk-…"            # ← paste key

# toy db
db = pathlib.Path("demo.sqlite")
with sqlite3.connect(db) as con:
    con.execute("CREATE TABLE nums(n INT);")
    con.executemany("INSERT INTO nums VALUES (?)", [(1,),(2,),(3,)])

from methods.ReFoRCE.api import query_one
out = query_one(sqlite_path=db, question="What is the sum of n?")

print(out["sql"])
out["answer"]
```

---

## 4 Project layout (high-level)

```
Reforcer/
├── demo.py                     # quick local smoke test
├── methods/
│   └── ReFoRCE/
│       ├── run.py              # upstream main script
│       ├── api.py              # our new one-shot wrapper
│       ├── utils.py …          # minor tweaks
│       ├── requirements.txt    # python deps
│       └── …                   # rest of upstream code
└── README.md                   # this file
```

---

## 5 FAQ

### • Does the wrapper work with *any* SQLite DB?
Yes – `api.query_one` copies the `.sqlite` file to a temp folder, introspects the schema (`CREATE TABLE …`) and builds the *prompts.txt* ReFoRCE expects.

### • Multiple tables? Foreign keys?
No problem: every `CREATE TABLE …` statement is inserted verbatim, so the model sees the full schema.

### • How to keep the temp artefacts?
The dict’s `workdir` key points to the temp folder. As long as your process lives you can inspect it; delete when done.

### • Troubleshooting bad SQL
Open the `log` path – it’s the exact ReFoRCE chat transcript plus execution attempts.

Feel free to open issues / PRs – happy querying! 🚀


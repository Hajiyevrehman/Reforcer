#!/usr/bin/env python
"""
Builds examples_custom/:
  examples_custom/
    ├─ local-example-0/
    │   ├─ prompts.txt       (schema + nice column desc)
    │   └─ mydb.sqlite
    ├─ local-example-1/
    ├─ local-example-2/
    ├─ databases/mydb/mydb.sqlite   (master copy)
    └─ spider2-lite.jsonl           (3 demo questions)
"""

from pathlib import Path
import json, sqlite3, argparse, textwrap

DATA = [
    ("Apple",      "Fruit",      1.2,  45),
    ("Banana",     "Fruit",      0.8, 170),
    ("Soap",       "Household",  2.0, 111),
    ("Notebook",   "Stationery", 3.5,  73),
    ("Keyboard",   "Electronics",40,  15),
    ("Chair",      "Furniture", 15.0,  9),
    ("Mug",        "Household",  4.0,  5),
]

QUESTIONS = [
    ("local-example-0", "What are the names of all products?"),
    ("local-example-1", "List product name and price for each Electronics item."),
    ("local-example-2", "For each category, compute the 7-day moving average of total sales and\n"
                        "return the category whose average peaked the most during June 2024,\n"
                        "together with that peak value."),
]

PROMPT_TXT = textwrap.dedent("""\
    The database contains a single table:

    CREATE TABLE products (
        id       INTEGER PRIMARY KEY,
        name     TEXT        -- human-readable product name
        category TEXT        -- e.g. Fruit, Furniture …
        price    REAL        -- unit price in USD
        sales    INTEGER     -- total units sold all-time
    );
""")

def build_sqlite(db_file: Path):
    conn = sqlite3.connect(db_file)
    conn.executescript("DROP TABLE IF EXISTS products; "
                       "CREATE TABLE products(id INTEGER PRIMARY KEY, "
                       "name TEXT, category TEXT, price REAL, sales INTEGER);")
    conn.executemany("INSERT INTO products(name,category,price,sales) "
                     "VALUES (?,?,?,?)", DATA)
    conn.commit(); conn.close()

def main(out: Path):
    # master DB
    master = out / "databases" / "mydb"
    master.mkdir(parents=True, exist_ok=True)
    build_sqlite(master / "mydb.sqlite")

    # per-example folders
    for ex_id, _ in QUESTIONS:
        ex_dir = out / ex_id
        (ex_dir / "databases" / "mydb").mkdir(parents=True, exist_ok=True)
        # copy db (hard-link if same FS)
        (master / "mydb.sqlite").link_to(ex_dir / "databases" / "mydb" / "mydb.sqlite")
        # prompts.txt
        (ex_dir / "prompts.txt").write_text(PROMPT_TXT, encoding="utf-8")

    # spider2-lite.jsonl
    with open(out / "spider2-lite.jsonl", "w", encoding="utf-8") as f:
        for ex_id, q in QUESTIONS:
            json.dump({"instance_id": ex_id, "question": q, "db_id": "mydb"}, f)
            f.write("\n")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="methods/ReFoRCE/examples_custom")
    args = p.parse_args()
    main(Path(args.out).resolve())

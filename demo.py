import pathlib, sqlite3, tempfile
from methods.ReFoRCE.api import query_one

# build a tiny DB in /tmp
db = pathlib.Path(tempfile.gettempdir()) / "demo.sqlite"
with sqlite3.connect(db) as con:
    con.executescript("""
        DROP TABLE IF EXISTS products;
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            price REAL,
            sales INTEGER
        );
        INSERT INTO products(name,category,price,sales) VALUES
        ('Apple','Fruit',1.2,45),
        ('Banana','Fruit',0.8,170),
        ('Chair','Furniture',42,12);
    """)

out = query_one(
    sqlite_path=db,
    question="List each category and its average price.",
    max_iter=8,               # let self-refine loop a bit more
    show_log_tail=True        # print log tail so we can watch iterations
)

print("SQL\n---\n", out["sql"])
print("\nAnswer\n------")
print(out["answer"])

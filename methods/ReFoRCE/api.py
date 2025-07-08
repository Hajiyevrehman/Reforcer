# methods/ReFoRCE/api.py
from __future__ import annotations
import subprocess, json, shutil, tempfile, uuid, sqlite3, textwrap
from pathlib import Path
import pandas as pd

# methods/ReFoRCE/api.py
from pathlib import Path
from pathlib import Path
_RUN_PY = (Path(__file__).resolve().parent / "run.py").resolve()

def _ensure_pandas():
    try:
        import pandas  # noqa: F401
    except ModuleNotFoundError:
        subprocess.check_call(["pip", "install", "pandas"])
        import pandas  # noqa: F401

def _ddl_from_sqlite(db: Path) -> str:
    """Return CREATE-TABLE statements for *all* tables in the db."""
    con = sqlite3.connect(db)
    cur = con.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    ddls = [row[1] for row in cur.fetchall() if row[1]]
    con.close()
    return "\n\n".join(ddls) or "-- (empty schema)"

def query_one(*,
              sqlite_path: str | Path,
              question: str,
              model: str = "gpt-4o") -> dict:
    """
    Run ReFoRCE once on a single question.

    Returns
    -------
    dict with keys:
      sql   → str      # model-generated SQL
      answer→ pd.DataFrame
      log   → Path     # full log file
      workdir→ Path    # temp work directory (auto-deleted on exit unless you keep it)
    """
    _ensure_pandas()
    import pandas as pd                        # after install

    sqlite_path = Path(sqlite_path).expanduser().resolve()
    assert sqlite_path.exists(), f"DB not found: {sqlite_path}"

    workdir = Path(tempfile.mkdtemp(prefix="reforce_tmp_"))
    ex_id   = f"local-{uuid.uuid4().hex[:8]}"
    ex_dir  = workdir / ex_id

    db_copy = ex_dir / "mydb.sqlite"
    db_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sqlite_path, db_copy)

    # generate prompts.txt from actual schema
    ddl = _ddl_from_sqlite(db_copy)
    (ex_dir / "prompts.txt").write_text(
        textwrap.dedent(f"""\
        The database contains the following tables:

        {ddl}
        """)
    )

    # minimal 1-line spider2-lite.jsonl
    (workdir / "spider2-lite.jsonl").write_text(json.dumps({
        "instance_id": ex_id,
        "question":   question
    }) + "\n")

    # launch ReFoRCE
    cmd = [
        "python", str(_RUN_PY),
        "--task", "lite",
        "--subtask", "sqlite",
        "--db_path", str(workdir),
        "--output_path", str(workdir / "out"),
        "--generation_model", model,
        "--do_self_refinement",
        "--num_workers", "1"
    ]
    subprocess.run(cmd, check=True)

    # read back results
    outdir  = workdir / "out" / ex_id
    sql_txt = next(outdir.glob("*.sql")).read_text()
    csv     = pd.read_csv(next(outdir.glob("*.csv")))

    return {"sql": sql_txt,
            "answer": csv,
            "log": outdir / "log.log",
            "workdir": workdir}

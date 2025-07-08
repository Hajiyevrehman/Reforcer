# methods/ReFoRCE/api.py
from __future__ import annotations
import subprocess, json, shutil, tempfile, uuid, sqlite3, textwrap
from pathlib import Path

_RUN_PY = (Path(__file__).resolve().parent / "run.py").resolve()

def _ensure_pandas():
    try:
        import pandas  # noqa: F401
    except ModuleNotFoundError:
        subprocess.check_call(["pip", "install", "pandas"])
        import pandas  # noqa: F401

def _ddl_from_sqlite(db: Path) -> str:
    con = sqlite3.connect(db)
    ddl = "\n\n".join(                  
        row[0] for row in                
        con.execute("""
            SELECT sql
            FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        if row[0]                        
    )
    con.close()
    return ddl or "-- (empty schema)"



# ─── methods/ReFoRCE/api.py ─────────────────────────────────────────────
def query_one(*,
              sqlite_path : str | Path,
              question    : str,
              model       : str = "gpt-4o",
              extra_schema: str | None = None,
              num_workers : int = 1,
              max_iter    : int = 5,
              self_refine : bool = True,
              show_log_tail: bool = False,
              log_tail_lines: int = 40) -> dict:
    """
    Run ReFoRCE on a single NL question.

    Parameters
    ----------
    sqlite_path      : path to .sqlite
    question         : natural-language question
    model            : OpenAI model name (e.g. "gpt-4o")
    extra_schema     : optional extra description appended to the CREATE statements
    num_workers      : forwarded to run.py --num_workers
    max_iter         : forwarded to run.py --max_iter
    self_refine      : bool → add / drop --do_self_refinement
    show_log_tail    : if True, print the last N lines of log.log
    log_tail_lines   : how many lines to print

    Returns
    -------
    dict {sql:str, answer:pandas.DataFrame, log:Path, workdir:Path}
    """
    import pandas as _pd, subprocess, tempfile, shutil, sqlite3, uuid, json, textwrap, os
    from pathlib import Path

    sqlite_path = Path(sqlite_path).expanduser().resolve()
    if not sqlite_path.exists():
        raise FileNotFoundError(sqlite_path)

    # temp work area ----------------------------------------------------
    workdir = Path(tempfile.mkdtemp(prefix="reforce_tmp_"))
    ex_id   = f"local-{uuid.uuid4().hex[:8]}"
    ex_dir  = workdir / ex_id
    ex_dir.mkdir(parents=True)

    # copy DB
    db_copy = ex_dir / "mydb.sqlite"
    shutil.copy2(sqlite_path, db_copy)

    # build prompts.txt -------------------------------------------------
    def _ddl_from(db: Path) -> str:
        con = sqlite3.connect(db)
        ddl = "\n\n".join(row[0]
                          for row in con.execute(
                              "SELECT sql FROM sqlite_master "
                              "WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                          if row[0])
        con.close()
        return ddl or "-- (empty schema)"

    ddl = _ddl_from(db_copy)
    if extra_schema:
        ddl += f"\n\n-- Extra notes\n{extra_schema.strip()}"

    (ex_dir / "prompts.txt").write_text(
        textwrap.dedent(f"""
        The database contains the following tables / columns:

        {ddl}
        """).lstrip()
    )

    # spider2-lite.jsonl -----------------------------------------------
    (workdir / "spider2-lite.jsonl").write_text(
        json.dumps({"instance_id": ex_id, "question": question}) + "\n"
    )

    # launch run.py -----------------------------------------------------
    cmd = [
        "python", str(_RUN_PY),
        "--task", "lite", "--subtask", "sqlite",
        "--db_path", str(workdir),
        "--output_path", str(workdir / "out"),
        "--generation_model", model,
        "--num_workers", str(num_workers),
        "--max_iter", str(max_iter),
    ]
    if self_refine:
        cmd.append("--do_self_refinement")

    subprocess.run(cmd, check=True)

    # collect output ----------------------------------------------------
    outdir  = workdir / "out" / ex_id
    sql_files = list(outdir.glob("*.sql"))
    if not sql_files:
        raise RuntimeError(f"ReFoRCE produced no SQL; inspect {outdir/'log.log'}")

    sql_txt = sql_files[0].read_text()
    answer  = _pd.read_csv(next(outdir.glob("*.csv")))

    if show_log_tail:
        print(f"\n─ log tail ({log_tail_lines} lines) • {outdir/'log.log'} ─")
        print("\n".join(outdir.joinpath("log.log").read_text().splitlines()[-log_tail_lines:]))

    return {"sql": sql_txt,
            "answer": answer,
            "log": outdir / "log.log",
            "workdir": workdir}

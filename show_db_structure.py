import sqlite3

db_path = "instance/tictactoe.sqlite3"
con = sqlite3.connect(db_path)

tables = [
    row[0]
    for row in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
]

print("База данных:", db_path)
print("Структура таблиц:")

for table in tables:
    print(f"\n[{table}]")
    for cid, name, type_, notnull, default, pk in con.execute(f"PRAGMA table_info({table})"):
        key = "PK" if pk else ""
        print(f"  {name:25} {type_:15} {key}")

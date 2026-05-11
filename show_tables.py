import sqlite3

con = sqlite3.connect("instance/tictactoe.sqlite3")

print("Таблицы базы данных:")
for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
    print("-", row[0])

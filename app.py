import json
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "dice_tasks.sqlite3"
SEED_PATH = BASE_DIR / "seed_tasks.json"
PORT = 8767

app = Flask(__name__, template_folder=str(BASE_DIR))


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS task_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                position INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_set_id INTEGER NOT NULL,
                roll INTEGER NOT NULL,
                level TEXT NOT NULL,
                title TEXT NOT NULL,
                condition TEXT NOT NULL,
                example TEXT,
                position INTEGER NOT NULL,
                FOREIGN KEY (task_set_id) REFERENCES task_sets(id)
            );
            """
        )

        task_set_count = connection.execute("SELECT COUNT(*) FROM task_sets").fetchone()[0]
        if task_set_count == 0:
            seed_db(connection)


def seed_db(connection):
    with SEED_PATH.open("r", encoding="utf-8") as seed_file:
        task_sets = json.load(seed_file)

    for set_position, task_set in enumerate(task_sets, start=1):
        cursor = connection.execute(
            """
            INSERT INTO task_sets (title, description, position)
            VALUES (?, ?, ?)
            """,
            (task_set["title"], task_set["description"], set_position),
        )
        task_set_id = cursor.lastrowid

        for task_position, task in enumerate(task_set["tasks"], start=1):
            connection.execute(
                """
                INSERT INTO tasks (
                    task_set_id, roll, level, title, condition, example, position
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_set_id,
                    task["roll"],
                    task["level"],
                    task["title"],
                    task["condition"],
                    task.get("example", ""),
                    task_position,
                ),
            )


def load_task_sets():
    with get_connection() as connection:
        set_rows = connection.execute(
            """
            SELECT id, title, description
            FROM task_sets
            ORDER BY position, id
            """
        ).fetchall()

        task_rows = connection.execute(
            """
            SELECT task_set_id, roll, level, title, condition, example
            FROM tasks
            ORDER BY position, id
            """
        ).fetchall()

    tasks_by_set = {}
    for task in task_rows:
        tasks_by_set.setdefault(task["task_set_id"], []).append(
            {
                "roll": task["roll"],
                "level": task["level"],
                "title": task["title"],
                "condition": task["condition"],
                "example": task["example"],
            }
        )

    return [
        {
            "title": task_set["title"],
            "description": task_set["description"],
            "tasks": tasks_by_set.get(task_set["id"], []),
        }
        for task_set in set_rows
    ]


@app.route("/")
def index():
    return render_template("dice_tasks_page.html", task_sets=load_task_sets())


@app.route("/api/task-sets")
def task_sets_api():
    return jsonify(load_task_sets())


init_db()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT, debug=True)

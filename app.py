from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "training-only-change-this-key"


def query(sql, params=(), one=False):
    with sqlite3.connect("site.db") as db:
        db.row_factory = sqlite3.Row
        result = db.execute(sql, params)
        if sql.strip().upper().startswith("SELECT"):
            return result.fetchone() if one else result.fetchall()
        db.commit()


with sqlite3.connect("site.db") as db:
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, done INTEGER DEFAULT 0)")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["username"].strip()
        password = request.form["password"]
        if not name or not password:
            return render_template("login.html", register=True, error="Заполните все поля")
        try:
            query("INSERT INTO users(username, password) VALUES(?, ?)", (name, generate_password_hash(password)))
            return redirect("/login")
        except sqlite3.IntegrityError:
            return render_template("login.html", register=True, error="Имя уже занято")
    return render_template("login.html", register=True)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = query("SELECT * FROM users WHERE username=?", (request.form["username"],), one=True)
        if user and check_password_hash(user["password"], request.form["password"]):
            session["uid"] = user["id"]
            session["username"] = user["username"]
            return redirect("/")
        return render_template("login.html", error="Неверный логин или пароль")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
def index():
    if "uid" not in session:
        return redirect("/login")
    search = request.args.get("search", "").strip()
    if search:
        tasks = query("SELECT * FROM tasks WHERE user_id=? AND LOWER(title) LIKE LOWER(?) ORDER BY id DESC", (session["uid"], f"%{search}%"))
    else:
        tasks = query("SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC", (session["uid"],))
    all_tasks = query("SELECT * FROM tasks WHERE user_id=?", (session["uid"],))
    completed = sum(task["done"] for task in all_tasks)
    return render_template("index.html", tasks=tasks, completed=completed, search=search)


@app.route("/add", methods=["POST"])
def add():
    if "uid" not in session:
        return redirect("/login")
    title = request.form.get("title", "").strip()
    if title:
        query("INSERT INTO tasks(user_id, title) VALUES(?, ?)", (session["uid"], title))
    return redirect("/")


@app.route("/done/<int:task_id>", methods=["POST"])
def done(task_id):
    if "uid" not in session:
        return redirect("/login")
    query("UPDATE tasks SET done=1 WHERE id=? AND user_id=?", (task_id, session["uid"]))
    return redirect("/")


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete(task_id):
    if "uid" not in session:
        return redirect("/login")
    query("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, session["uid"]))
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)

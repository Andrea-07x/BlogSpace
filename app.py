from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "blog_platform_secret_key"

DATABASE = "blog.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            user_id INTEGER NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def index():
    init_db()

    conn = get_db()

    posts = conn.execute("""
        SELECT posts.*, users.username
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.id DESC
    """).fetchall()

    conn.close()

    return render_template("index.html", posts=posts)


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = get_db()

        try:
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )

            conn.commit()
            conn.close()

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            conn.close()
            return "Username already exists!"

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect(url_for("index"))

        return "Invalid username or password!"

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("index"))


@app.route("/create", methods=["GET", "POST"])
def create_post():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form["title"]
        content = request.form["content"]

        conn = get_db()

        conn.execute("""
            INSERT INTO posts (title, content, user_id)
            VALUES (?, ?, ?)
        """, (
            title,
            content,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    return render_template("create_post.html")


@app.route("/post/<int:post_id>")
def view_post(post_id):

    conn = get_db()

    post = conn.execute("""
        SELECT posts.*, users.username
        FROM posts
        JOIN users ON posts.user_id = users.id
        WHERE posts.id = ?
    """, (post_id,)).fetchone()

    comments = conn.execute("""
        SELECT comments.*, users.username
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.post_id = ?
        ORDER BY comments.id DESC
    """, (post_id,)).fetchall()

    conn.close()

    if not post:
        return "Post not found!"

    return render_template(
        "post.html",
        post=post,
        comments=comments
    )


@app.route("/edit/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    post = conn.execute(
        "SELECT * FROM posts WHERE id = ?",
        (post_id,)
    ).fetchone()

    if not post:
        conn.close()
        return "Post not found!"

    if post["user_id"] != session["user_id"]:
        conn.close()
        return "You can only edit your own posts!"

    if request.method == "POST":

        title = request.form["title"]
        content = request.form["content"]

        conn.execute("""
            UPDATE posts
            SET title = ?, content = ?
            WHERE id = ?
        """, (
            title,
            content,
            post_id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("view_post", post_id=post_id))

    conn.close()

    return render_template(
        "edit_post.html",
        post=post
    )


@app.route("/delete/<int:post_id>")
def delete_post(post_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    post = conn.execute(
        "SELECT * FROM posts WHERE id = ?",
        (post_id,)
    ).fetchone()

    if not post:
        conn.close()
        return "Post not found!"

    if post["user_id"] != session["user_id"]:
        conn.close()
        return "You can only delete your own posts!"

    conn.execute(
        "DELETE FROM comments WHERE post_id = ?",
        (post_id,)
    )

    conn.execute(
        "DELETE FROM posts WHERE id = ?",
        (post_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("index"))


@app.route("/comment/<int:post_id>", methods=["POST"])
def add_comment(post_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    content = request.form["content"]

    conn = get_db()

    conn.execute("""
        INSERT INTO comments (content, post_id, user_id)
        VALUES (?, ?, ?)
    """, (
        content,
        post_id,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("view_post", post_id=post_id))


@app.route("/api/posts")
def api_posts():

    conn = get_db()

    posts = conn.execute("""
        SELECT posts.id,
               posts.title,
               posts.content,
               users.username
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.id DESC
    """).fetchall()

    conn.close()

    result = []

    for post in posts:

        result.append({
            "id": post["id"],
            "title": post["title"],
            "content": post["content"],
            "author": post["username"]
        })

    return jsonify(result)


if __name__ == "__main__":

    init_db()

    app.run(debug=True)
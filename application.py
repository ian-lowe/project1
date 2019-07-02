import os

from flask import Flask, render_template, session, request, redirect, url_for
from flask_session import Session
from flask_bcrypt import Bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
app.secret_key = os.urandom(16)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

#Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#initialize pw hashing
bcrypt = Bcrypt(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search", methods=["POST"])
def login():
    username = request.form.get("username").lower()
    password = request.form.get("password")

    user = db.execute("SELECT * FROM users WHERE username = :username",
    {"username": username}).fetchone()

    if user is None:
        return render_template("index.html", message_l="Account doesn't exist. Please create an account.",
        class_name="error")

    is_pass = bcrypt.check_password_hash(user.password, password)

    if is_pass == False:
        return render_template("index.html", message_l="Invalid password.",
        class_name="error")

    session["users"] = user.username

    return render_template("search.html", username=user.username)

@app.route("/", methods=["POST"])
def register():
    username = request.form.get("username-reg").lower()
    password = request.form.get("password-reg")

    if len(username) > 20:
        return render_template("index.html", message_r="Invalid username. Max length 20 characters.", class_name="error")

    if len(password) < 6:
        return render_template("index.html", message_r="Invalid password. Minimum length 6 characters.",
        class_name="error")

    username_checkdb = db.execute("SELECT * FROM users WHERE username = :username", {
        "username": username}).fetchone()

    if username_checkdb is None:
        hashed_pass = bcrypt.generate_password_hash(password).decode('utf-8')
        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username": username, "password": hashed_pass})
        db.commit()
        return render_template("index.html", message_r="Success! Please log in.",
        class_name="success")

    else:
        return render_template("index.html", message_r="Username taken. Please choose another.",
        class_name="error")

@app.route('/logout')
def logout():
    session.pop("users", None)
    return render_template("index.html", message="For security reasons, please be sure to close this window when finished!", class_name="warning")


@app.route('/results', methods=["POST"])
def results():
    query = "%"
    query += request.form.get("search-input")
    query += "%"

    option = request.form['options']
    if option is "":
        return "test"

    if option == "isbn":
        results = db.execute("SELECT * FROM books WHERE isbn LIKE :isbn", {"isbn": query}).fetchall()
        return render_template("results.html", results=results)
    elif option == "title":
        results = db.execute("SELECT * FROM books WHERE LOWER(title) LIKE LOWER(:title)", {"title": query}).fetchall()
        return render_template("results.html", results=results)
    elif option == "author":
        results = db.execute("SELECT * FROM books WHERE LOWER(author) LIKE LOWER(:author)", {"author": query}).fetchall()
        return render_template("results.html", results=results)
    else:
        return "test"

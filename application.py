import os
import string
import requests
import sys


from flask import Flask, render_template, session, request, redirect, url_for, flash
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
    # if user is already logged in, redirect
    if session.get('user') != None:
        return redirect(url_for('login'))

    # else render login page
    return render_template("index.html")

@app.route("/search", methods=["POST", "GET"])
def login():
    # log user in and send to search page
    if request.method == "POST":
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

        session["user"] = user.username

        return render_template("search.html")
    # method is GET
    else:
        # if not logged in, redirect to login page
        if session.get('user') == None:
            flash("Please log in to use search feature.")
            return redirect(url_for('index'))
        # reload search page
        else:
            return render_template("search.html")


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

@app.route('/logout', methods=["POST"])
def logout():
    session.pop("user", None)
    return redirect(url_for('index'))


@app.route('/books', methods=["POST"])
def books():
    if session.get('user') == None:
        flash("Session expired. Please log in to use search feature.")
        return redirect(url_for('index'))

    query = "%"
    query += request.form.get("search-input").strip()
    query += "%"

    option = request.form['options']

    if option == "isbn":
        books = db.execute("SELECT * FROM books WHERE isbn LIKE :isbn", {"isbn": query}).fetchall()
        return render_template("books.html", books=books, option=option)

    elif option == "title":
        books = db.execute("SELECT * FROM books WHERE LOWER(title) LIKE LOWER(:title)", {"title": query}).fetchall()
        return render_template("books.html", books=books, option=option)

    elif option == "author":
        books = db.execute("SELECT * FROM books WHERE LOWER(author) LIKE LOWER(:author)", {"author": query}).fetchall()
        return render_template("books.html", books=books, option=option)

    else:
        return "test"

@app.route("/books/<string:isbn>", methods=['GET', 'POST'])
def book(isbn):
    if request.method == 'GET':
        book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()

        reviews = db.execute("SELECT review, score, username FROM reviews JOIN users ON reviews.user_id = users.user_id WHERE book_isbn = :isbn", {"isbn": isbn}).fetchall()

        res = requests.get("https://www.goodreads.com/book/review_counts.json",
                        params={
                            "key": "GJZSpTvdcwByldSQzwRBfg",
                            "isbns": isbn
                        })
        if res.status_code != 200:
            return render_template("book.html", book=book) 

        res_json = res.json()
        res_avg = res_json['books'][0]['average_rating']
        res_count = res_json['books'][0]['ratings_count']

        return render_template("book.html", book=book, res_avg=res_avg, res_count=(format (res_count, ',d')), reviews=reviews)
    else:
        review = request.form.get("review-input")
        score = request.form['ratings']
        user_id = db.execute(
            "SELECT user_id FROM users WHERE username = :username", {
                "username": session["user"]
            }).fetchone()


        db.execute("INSERT INTO reviews (score, review, user_id, book_isbn) VALUES (:score, :review, :user_id, :book_isbn)", {"score": score, "review": review, "user_id": user_id[0], "book_isbn": isbn})
        db.commit()

        return redirect(url_for('book', isbn=isbn))

# @app.route("/books/<string:isbn>/reviews")
# def reviews(isbn):


# @app.route("/api/<string:isbn>")
# def api():

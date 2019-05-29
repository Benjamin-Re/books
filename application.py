import os

from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from helpers import failure

app = Flask(__name__)


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")
# postgres://ordkdczfhjcurx:486ce11917bcda3ad0e793d1cb912ff04cac1016de04ef10bcf06adaad3c1748@ec2-79-125-2-142.eu-west-1.compute.amazonaws.com:5432/d92938oil3bqhi

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    # import requests
    # res = requests.get("https://www.goodreads.com/book/review_counts.json",
    #                   params={"key": "EuLUAZmqlGa3tElfJPoShQ", "isbns": "9781416524793"})
    # print(res.json())
    return render_template("index.html")

@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name")
    password = request.form.get("password")
    if not request.form.get("name"):
        return failure("please provide username", 400)
    if not request.form.get("password"):
        return failure("please provide password", 400)
    # Issue: Security needed here pw -> hash
    # checking if username already exists
    names = db.execute("SELECT name FROM readers").fetchall()
    for n in names:
        print(n[0])
        if name == n[0]:
            return failure("username not unique", 400)
    db.execute("INSERT INTO readers (name, password) VALUES (:name, :password)",
           {"name": name, "password": password})
    db.commit()
    # if success log user in
    # Issue: Better use user_id for login
    session["username"] = name
    # if successful redirect to dashboard function
    return redirect(url_for("dashboard"))

@app.route("/login", methods=['POST'])
def login():
    # Get name & pw from form
    name = request.form.get("name")
    password = request.form.get("password")
    if not request.form.get("name"):
        return failure("please provide username", 400)
    if not request.form.get("password"):
        return failure("please provide password", 400)
    # Get user's pw from db. The result of execute is a sqlAlchemy proxy
    # I have no idea what that means, but .fetchall() converts it into a tuple,
    # which is indexable
    db_password = db.execute("SELECT password, id FROM readers WHERE name=:name", {"name": name}).fetchall()
    if password == db_password[0]['password']:
        session["user_id"] = db_password[0]['id']
        session["username"] = name
        # if success redirect to dashboard function
        return redirect(url_for("dashboard"))
    else:
        return failure("credentials not correct", 400)


@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    # if notes are empty create them
    # the name of the notes is itself a variable, the username, which is stored in session['username']
    # so every user gets his/ her own notes
    if session.get(session["username"]) is None:
        session[session["username"]] = []
    # when writing a note append it to notes
    if request.method == "POST":
        note = request.form.get('note')
        session[session["username"]].append(note)
    return render_template("dashboard.html", notes=session[session["username"]], name=session["username"])


@app.route("/search", methods=['POST'])
def search():
    # get query from form and add wildcard character
    # temporary query variable
    tempquery = request.form.get('search')
    # final query variable, already add one % in case we are missing keyword in front
    query = '%'
    # if tempquery contains multiple words we need to add the wildcard character % in between and at the end
    if len(tempquery.split()) > 1:
        tempquery = tempquery.split()
        for i in tempquery:
            query = query + i + '%'
    # else just pass the temporary to the final unchanged
    else:
        query = '%'+tempquery+'%'
    # (minor) ISSUE: search result page shows book titles. Even tough query was for author
    db_query = db.execute("SELECT * FROM books WHERE UPPER(title) LIKE UPPER(:query) "
                          "OR isbn LIKE :query OR UPPER(author) LIKE UPPER(:query) LIMIT 10", {"query": query}).fetchall()
    if not db_query:
        return failure("No search results to your query.", 200)
    return render_template("results.html", query=db_query)

@app.route("/logout", methods=['POST', 'GET'])
def logout():
    session.pop('username', None)
    return render_template("index.html")


@app.route("/book/<title>/<author>/<isbn>/<year>")
def book(title, author, isbn, year):
    package = db.execute("SELECT rating, review, name FROM reviews WHERE book LIKE :title",
                         {"title": title}).fetchall()
    import requests
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": "EuLUAZmqlGa3tElfJPoShQ", "isbns": isbn})
    average_rating = res.json()['books'][0]['average_rating']
    ratings_count = res.json()['books'][0]['ratings_count']

    return render_template("book.html", title=title, author=author, isbn=isbn, year=year, package=package,
                           average_rating=average_rating, ratings_count=ratings_count)


@app.route("/review/<title>/<author>/<isbn>/<year>", methods=['POST', 'GET'])
def review(title, author, isbn, year):
    if request.method == "POST":
        book = title
        rating = int(request.form.get("rating"))
        review = request.form.get("review")
        name = session["username"]
        user_id = int(session["user_id"])
        condition = db.execute("SELECT * FROM reviews WHERE name LIKE :name AND book LIKE :title",
                      {"name": name, "title": title}).fetchall()
        # if the condition is flase, i.e. [] empty, then go ahead and post a review
        if not condition:
            db.execute("INSERT INTO reviews (book, rating, review, name, user_id)" 
                       "VALUES(:book, :rating, :review, :name, :user_id)",
                       {"book": book, "rating": rating, "review": review, "name": name, "user_id": user_id})
            db.commit()
            return redirect(url_for('book', title=title, author=author, isbn=isbn, year=year))
        else:
            # otherwise return a failure
            return failure("Can't post multiple reviews for one book", 401)
    else:
        return redirect(url_for('book', title=title, author=author, isbn=isbn, year=year))


@app.route("/api/<isbn>")
def api(isbn):
    # return details for an isbn
    # make sure isbn exists
    condition = db.execute("SELECT * FROM books WHERE isbn LIKE :isbn", {"isbn": isbn}).fetchall()
    if not condition:
        return jsonify({"error": "isbn not found"}), 422
    else:
        # return json response
        return jsonify({"isbn": condition[0][0],
                        "title": condition[0][1],
                        "author": condition[0][2],
                        "year": condition[0][3]}), 200



# TODO
# Rating stars? Merge my rating with average
# Layout & Design
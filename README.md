# Project 1
Web Programming with Python and JavaScript
A Flask app for searching for and reviewing of books.

The parts:
application.py contains all the routes. It imports SQLAlchemy, Flask Sessions, and helpers.py.

books.csv contains 5000 books that are imported into the postgres db via import.py

helpers.py defines a function for failures, so the failure template can be rendered easily along with an error message and code.

The templates folder contains all html files.
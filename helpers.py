import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps

def failure(message, code):
    return render_template("failure.html", code=code, message=message)
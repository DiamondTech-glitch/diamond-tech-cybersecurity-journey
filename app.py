"""
Personal AI Study Assistant — Web app.
Uses assistant_core.py for memory, conversations, settings, and Claude calls.
"""

import os

from flask import Flask, request, jsonify, render_template, session

from assistant_core import (
    save_message, ask_claude, add_progress_note, recent_progress, clear_progress,
    create_conversation, list_conversations, delete_conversation, clear_all_conversations,
    recent_history, get_assistant_name, set_assistant_name,
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

APP_PASSWORD = os.environ.get("APP_PASSWORD")  # optional simple gate


def check_auth(req):
    if not APP_PASSWORD:
        return True
    return req.headers.get("X-App-Password") == APP_PASSWORD


def get_user_id():
    return "web-" + session.setdefault("user_id", os.urandom(8).hex())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/conversations", methods=["GET", "POST"])
def conversations():
    user_id = get_user_id()

    if request.method == "POST":
        title = (request.get_json() or {}).get("title", "New chat")
        conv_id = create_conversation(user_id, title)
        return jsonify({"id": conv_id, "title": title})

    return jsonify(list_conversations(user_id))


@app.route("/api/conversations/<int:conv_id>", methods=["DELETE"])
def delete_conv(conv_id):
    user_id = get_user_id()
    delete
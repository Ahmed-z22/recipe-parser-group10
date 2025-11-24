from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
from src.chatbot import Chatbot

parent_dir = os.path.join(os.path.dirname(__file__), "..")
src_dir = os.path.join(parent_dir, "src")
sys.path.insert(0, parent_dir)
sys.path.insert(0, src_dir)


app = Flask(__name__)
CORS(app)

chatbots = {}


def make_chatbot(url):
    chatbot = Chatbot(backend=True)
    chatbot.process_url(url)

    return chatbot


@app.route("/api/initialize", methods=["POST"])
def initialize():
    data = request.json
    url = data.get("url")
    sid = data.get("session_id", "default")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        bot = make_chatbot(url)
        chatbots[sid] = bot

        return jsonify(
            {"success": True, "title": bot.title.get("title", "Unknown Recipe")}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    question = data.get("question")
    sid = data.get("session_id", "default")

    if not question:
        return jsonify({"error": "Question is required"}), 400

    if sid not in chatbots:
        return jsonify({"error": "Chatbot not initialized"}), 400

    bot = chatbots[sid]

    try:
        response = bot.respond(question)

        if not response:
            response = "No response."

        return jsonify(
            {
                "response": response,
                "current_step": bot.current_step,
                "total_steps": len(bot.steps),
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5001)

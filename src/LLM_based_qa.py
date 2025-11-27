from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

parent_dir = os.path.join(os.path.dirname(__file__), "..")
src_dir = os.path.join(parent_dir, "src")
sys.path.insert(0, parent_dir)
sys.path.insert(0, src_dir)

from src.chatbot import Chatbot
from src.LLM_based_qa import LLMBasedQA

app = Flask(__name__)
CORS(app)

sessions = {}


def make_classical_bot(url):
    bot = Chatbot(backend=True, mode="classical")
    success = bot.process_url(url)
    if not success:
        raise RuntimeError("Failed to process recipe URL in classical mode")
    return bot


def make_hybrid_bot(url):
    bot = Chatbot(backend=True, mode="hybrid")
    success = bot.process_url(url)
    if not success:
        raise RuntimeError("Failed to process recipe URL in hybrid mode")
    return bot


def make_llm_bot(url):
    return LLMBasedQA(url)


@app.route("/api/initialize", methods=["POST"])
def initialize():
    data = request.json
    url = data.get("url")
    sid = data.get("session_id", "default")
    mode = data.get("mode", "classical")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    if mode not in ["classical", "llm", "hybrid"]:
        return jsonify({"error": "Invalid mode"}), 400

    try:
        if mode == "classical":
            bot = make_classical_bot(url)
            title = bot.title.get("title", "Unknown Recipe")
        elif mode == "llm":
            bot = make_llm_bot(url)
            title = bot.title.get("title", "Unknown Recipe")
        else:
            bot = make_hybrid_bot(url)
            title = bot.title.get("title", "Unknown Recipe")

        sessions[sid] = {"mode": mode, "bot": bot}

        return jsonify({"success": True, "title": title, "mode": mode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    question = data.get("question")
    sid = data.get("session_id", "default")

    if not question:
        return jsonify({"error": "Question is required"}), 400

    if sid not in sessions:
        return jsonify({"error": "Chatbot not initialized"}), 400

    session = sessions[sid]
    mode = session["mode"]
    bot = session["bot"]

    try:
        if mode in ["classical", "hybrid"]:
            response = bot.respond(question)
            if not response:
                response = "No response."

            return jsonify(
                {
                    "response": response,
                    "current_step": bot.current_step,
                    "total_steps": len(bot.steps),
                    "mode": mode,
                }
            )

        else:
            _, answer = bot.answer(question)
            response = answer or "No response."

            return jsonify(
                {
                    "response": response,
                    "current_step": 0,
                    "total_steps": 0,
                    "mode": mode,
                }
            )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5001)

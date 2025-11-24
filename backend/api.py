from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

parent_dir = os.path.join(os.path.dirname(__file__), '..')
src_dir = os.path.join(parent_dir, 'src')
sys.path.insert(0, parent_dir)
sys.path.insert(0, src_dir)

from chatbot import Chatbot

app = Flask(__name__)
CORS(app)

chatbots = {}

def make_chatbot(url):
    chatbot = Chatbot(backend=True)
    chatbot.process_url(url)
    
    return chatbot

@app.route('/api/initialize', methods=['POST'])
def initialize():
    data = request.json
    url = data.get('url')
    sid = data.get('session_id', 'default')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        bot = make_chatbot(url)
        chatbots[sid] = bot
        
        return jsonify({
            'success': True,
            'title': bot.title.get('title', 'Unknown Recipe')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question')
    sid = data.get('session_id', 'default')
    
    if not question:
        return jsonify({'error': 'Question is required'}), 400
    
    if sid not in chatbots:
        return jsonify({'error': 'Chatbot not initialized'}), 400
    
    bot = chatbots[sid]
    
    try:
        response = bot.respond(question)

        if not response:
            response = 'No response.'
    
        return jsonify({
            'response': response,
            'current_step': bot.current_step,
            'total_steps': len(bot.steps)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5001)

# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import sys
# import os
# import io
# from contextlib import redirect_stdout
#
# parent_dir = os.path.join(os.path.dirname(__file__), '..')
# src_dir = os.path.join(parent_dir, 'src')
# sys.path.insert(0, parent_dir)
# sys.path.insert(0, src_dir)
#
# from chatbot import Chatbot
# from scraper import get_recipe_data
# from ingredients_parser import IngredientsParser
# from steps_parser import StepsParser
# from methods_parser import MethodsParser
# from tools_parser import ToolsParser
#
# app = Flask(__name__)
# CORS(app)
#
# chatbots = {}
#
# def make_chatbot(url):
#     chatbot = Chatbot.__new__(Chatbot)
#     chatbot.test = False
#     chatbot.url = url
#     chatbot.current_step = 0
#     
#     chatbot.title, chatbot.raw_ingredients, chatbot.raw_steps = get_recipe_data(url)
#     
#     ingredients = IngredientsParser(chatbot.raw_ingredients)
#     chatbot.ingredients = ingredients.parse()
#     
#     methods = MethodsParser(chatbot.raw_steps)
#     chatbot.methods = methods.parse()
#     
#     steps = StepsParser(chatbot.raw_steps, chatbot.ingredients)
#     chatbot.steps = steps.parse()
#     
#     tools = ToolsParser(chatbot.raw_steps)
#     chatbot.tools = tools.parse()
#     
#     chatbot.responses = [
#         chatbot._retrieval_query,
#         chatbot._navigation_query,
#         chatbot._parameter_query,
#         chatbot._clarification_query,
#         chatbot._procedure_query,
#         chatbot._quantity_query,
#     ]
#     
#     return chatbot
#
# @app.route('/api/initialize', methods=['POST'])
# def initialize():
#     data = request.json
#     url = data.get('url')
#     sid = data.get('session_id', 'default')
#     
#     if not url:
#         return jsonify({'error': 'URL is required'}), 400
#     
#     try:
#         bot = make_chatbot(url)
#         chatbots[sid] = bot
#         
#         return jsonify({
#             'success': True,
#             'title': bot.title.get('title', 'Unknown Recipe')
#         })
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
#
# @app.route('/api/chat', methods=['POST'])
# def chat():
#     data = request.json
#     question = data.get('question')
#     sid = data.get('session_id', 'default')
#     
#     if not question:
#         return jsonify({'error': 'Question is required'}), 400
#     
#     if sid not in chatbots:
#         return jsonify({'error': 'Chatbot not initialized'}), 400
#     
#     bot = chatbots[sid]
#     
#     try:
#         cleaned = bot._clean_question(question)
#         qtype = bot._identify_query(cleaned)
#         
#         if qtype == -1:
#             response = 'Unclear question type.'
#         else:
#             f = io.StringIO()
#             with redirect_stdout(f):
#                 bot.responses[qtype](cleaned)
#             response = f.getvalue().strip()
#             
#             if not response:
#                 response = 'No response.'
#         
#         return jsonify({
#             'response': response,
#             'current_step': bot.current_step,
#             'total_steps': len(bot.steps)
#         })
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
#
# @app.route('/api/health', methods=['GET'])
# def health():
#     return jsonify({'status': 'ok'})
#
# if __name__ == '__main__':
#     app.run(debug=True, host='127.0.0.1', port=5001)

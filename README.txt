#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-

                                                        Project Structure

.
├── backend
│   └── api.py
├── frontend
│   ├── public
│   │   └── index.html
│   ├── src
│   │   ├── App.css
│   │   ├── App.js
│   │   ├── index.css
│   │   └── index.js
│   ├── package-lock.json
│   └── package.json
├── src
│   ├── helper_files
│   │   ├── method_keywords.json
│   │   ├── procedures.json
│   │   ├── tools_keywords.json
│   │   ├── unicode_fractions.json
│   │   ├── units_map.json
│   │   └── usages.json
│   ├── prompts
│   │   ├── descriptors_prompt.txt
│   │   ├── ingredients_names_prompt.txt
│   │   ├── LLM_based_qa_prompt.txt
│   │   ├── measurement_units_prompt.txt
│   │   ├── methods_prompt.txt
│   │   ├── preparations_prompt.txt
│   │   ├── quantities_prompt.txt
│   │   └── tools_prompt.txt
│   ├── __init__.py
│   ├── chatbot.py
│   ├── ingredients_parser.py
│   ├── LLM_based_qa.py
│   ├── methods_parser.py
│   ├── scraper.py
│   ├── steps_parser.py
│   └── tools_parser.py
├── .gitignore
├── allowed_questions.txt
├── environment.yml
├── pyproject.toml
├── README.md
└── README.txt
#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-




#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-

                                                        src/ folder

scraper.py

Scrapes recipe data (title, ingredients, directions) from supported domains (allrecipes, epicurious, bonappetit).

Main function: get_recipe_data(url)
• Validates domain, fetches page HTML, extracts JSON-LD recipe metadata.
• Returns structured dicts for title, ingredients list, and directions list.

Internal helpers:
• _http_get_soup(url): GET request → BeautifulSoup object.
• _extract_json_ld_recipe(...): Finds/normalizes JSON-LD “Recipe" fields (title, ingredients, instructions).
------------------------------------------------------------------------------------------------------------------------------

ingredients_parser.py

Defines IngredientsParser for converting raw ingredient lines into structured fields.
Uses spaCy + regex + helper JSON files (units_map.json, unicode_fractions.json).

Extracted fields:
• ingredient_name
• ingredient_quantity (int/float/None)
• measurement_unit (canonical)
• ingredient_descriptors
• ingredient_preparation

parse() returns a list of dicts containing the extracted fields mentioned above, one per ingredient line.
------------------------------------------------------------------------------------------------------------------------------

methods_parser.py

Defines MethodsParser for extracting cooking methods from directions.
Uses spaCy + method_keywords.json.

Behavior:
• Splits each direction into sentence-level steps.
• Identifies verbs representing allowed cooking methods.
• Deduplicates and orders methods per direction.

parse() returns, for each direction: original text, list of step sentences, and extracted methods.
------------------------------------------------------------------------------------------------------------------------------

tools_parser.py

Defines ToolsParser for extracting tools/equipment mentioned in directions.
Uses spaCy + tools_keywords.json and auxiliary tool-related word lists.

Detects noun chunks likely representing tools and normalizes them.
parse() returns, for each direction: original text, step sentences, and extracted tools.
------------------------------------------------------------------------------------------------------------------------------

steps_parser.py

Defines StepsParser to convert directions into atomic, annotated cooking steps.
Integrates results from IngredientsParser, ToolsParser, and MethodsParser.
Produces atomic steps by splitting sentences and coordinated verbs.

For each atomic step extracts:
• ingredients
• tools
• methods
• time expressions
• temperature expressions
• step type (action, observation, advice, warning)

parse() returns a numbered list of atomic step dicts.
------------------------------------------------------------------------------------------------------------------------------

chatbot.py

For answering questions about a scraped recipe. 

1 - Prompts user for a recipe URL (or uses a fixed URL in test mode). 
2 - Scrapes title, raw ingredients, and raw steps via get_recipe_data. 
3 - Parses structured ingredients, tools, methods, and atomic steps using the aforementioned classes. 
4 - Maintains current_step state for navigation.
5 - Parses questions and answer them
------------------------------------------------------------------------------------------------------------------------------

LLM_based_qa.py

Defines LLMBasedQA, a wrapper around Google Gemini for recipe-question answering.

Behavior:
1 - Loads API key from apikey.env and system prompt from prompts/prompt_part2.txt.
2 - Initializes a Gemini chat session with controlled decoding settings.
3 - Scrapes recipe title, ingredients, and directions using get_recipe_data(url).
4 - Formats recipe data + user question into a structured prompt.
5 - Sends queries to the model and returns the latest answer.

When run directly:
• Prompts for a recipe URL, starts an interactive terminal Q&A loop, and responds until the user exits.
#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-




#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-

                                                        backend/ folder

api.py

Flask API for both the classical parser-based chatbot and the LLM-based QA bot, with per-session state.

• make_classical_bot(url): builds a Chatbot instance and parses the recipe.
• make_llm_bot(url): builds an LLMBasedQA instance for LLM-only Q&A.

Endpoints:
• POST /api/initialize → takes url, session_id, and mode; creates bot instance, stores it, and returns recipe title + mode.
• POST /api/chat → routes question to the correct bot;
    - classical: returns response, current_step, total_steps
    – llm: returns the LLM answer with current_step = 0, total_steps = 0
• GET /api/health → health check.

Runs on 127.0.0.1:5001 when executed directly.
#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-




#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-

                                                        frontend/ folder

public/index.html

HTML container for the React app with <div id="root">.
------------------------------------------------------------------------------------------------------------------------------

src/index.js

React entry point; renders App.
------------------------------------------------------------------------------------------------------------------------------

src/index.css

Global styles.
------------------------------------------------------------------------------------------------------------------------------

src/App.css

Layout and visuals for the chat interface.
------------------------------------------------------------------------------------------------------------------------------

src/App.js

Main React UI for the recipe chatbot, supporting both Classical NLP and LLM (Gemini) modes.
Behavior:
• Handles URL input, recipe initialization, mode selection, chat messages, loading state, and (for classical mode) step tracking.
• Provides both text input and voice input via the Web Speech API, with optional auto-speak plus per-message Speak/Stop controls.
• Talks to the Flask backend via /api/initialize and /api/chat, sending a fixed session_id to preserve conversation state.
#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-




#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-
                                                    src/helper_files


method_keywords.json => contains common methods
tools_keywords.json => contains common tools, prep words, tools verb list
unicode_fractions.json => contains mapping between unicode fractions to numbers
units_map.json => contains measurement_units and a mapping from the different variations to canonical form
usages.json => contains the usages of common tools
procedures.json => contains explinations of common procedures (methods)

#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-

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
Offers 2 methods of extraction:
    - spaCy + regex + helper JSON files (units_map.json, unicode_fractions.json).
    - LLM-Based extraction using Gemini model

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
Offers 2 methods of extraction:
    - Uses spaCy + method_keywords.json.
    - LLM-Based extraction using Gemini model

Behavior:
• Splits each direction into sentence-level steps.
• Identifies verbs representing allowed cooking methods.
• Deduplicates and orders methods per direction.

parse() returns, for each direction: original text, list of step sentences, and extracted methods.
------------------------------------------------------------------------------------------------------------------------------

tools_parser.py

Defines ToolsParser for extracting tools/equipment mentioned in directions.
Offers 2 methods of extraction:
    - spaCy + tools_keywords.json and auxiliary tool-related word lists.
    - LLM-Based extraction using Gemini model

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

Flask + CORS API for the classical, hybrid, and LLM-based recipe chatbots, with per-session state.
    • make_classical_bot(url): builds a Chatbot in classical mode and parses the recipe.
    • make_hybrid_bot(url): builds a Chatbot in hybrid mode and parses the recipe.
    • make_llm_bot(url): builds an LLMBasedQA instance for LLM-only Q&A.

Endpoints:
    • POST /api/initialize → takes url, session_id, and mode ∈ {"classical", "hybrid", "llm"};
creates the appropriate bot, stores it in sessions, and returns recipe title + mode.
    • POST /api/chat → takes question and session_id; routes to the stored bot:
    - classical / hybrid: returns response, current_step, total_steps, mode
    - llm: returns LLM answer with current_step = 0, total_steps = 0, mode
    • GET /api/health → simple health check ({"status": "ok"}).

Runs on 127.0.0.1:5001 with debug=True when executed directly.
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

Main React UI for the recipe chatbot, supporting Classical NLP, LLM (Gemini), and Hybrid modes.
Behavior:
• Handles URL input, recipe initialization, mode selection, chat messages, loading state, and step tracking.
• Provides both text input and voice input via the Web Speech API, with optional auto-speak plus per-message Speak/Stop controls.
• Talks to the Flask backend via /api/initialize and /api/chat, sending a fixed session_id to preserve conversation state.
#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-




#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-
                                           
                                                    src/helper_files

method_keywords.json      => contains common cooking methods
tools_keywords.json       => contains common tools, preparation words, and tool-related verb lists
unicode_fractions.json    => maps Unicode fraction characters to numeric values
units_map.json            => contains measurement units and a mapping from variations to canonical forms
usages.json               => describes the common usages of kitchen tools
procedures.json           => contains explanations of common cooking procedures (methods)
#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-




#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-
   
                                                    src/prompts

LLM_based_qa_prompt.txt        => contains the full prompt for the LLM-Based QA; handles all QA-related logic

ingredients_names_prompt.txt   => extracts ingredient names from full ingredient sentences
preparations_prompt.txt        => extracts specific ingredient preparations from an ingredient sentence
descriptors_prompt.txt         => extracts ingredient descriptors from an ingredient sentence
methods_prompt.txt             => extracts cooking methods from a single step
tools_prompt.txt               => extracts kitchen tools from a single step
quantities_prompt.txt          => extracts quantities and amounts from a single ingredient sentence
    - Note: Requires a Gemini subscription (too costly to run without one)
measurement_units_prompt.txt   => extracts measurement units associated with a specific ingredient in a single ingredient step
    - Note: Requires a Gemini subscription (too costly to run without one)
#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-

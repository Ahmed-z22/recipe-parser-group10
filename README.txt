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
#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-






#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-

                                                        backend/ folder

api.py

Flask API wrapping the Chatbot and parsers.

make_chatbot(url): builds a chatbot instance with parsed recipe metadata.

Endpoints:
• POST /api/initialize → creates chatbot, returns title
• POST /api/chat → processes a question, returns response + step indices
• GET /api/health → health check

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

Main React UI for the recipe chatbot.

Manages URL input, initialization, messages, loading state, step tracking, speech recognition, and speech synthesis.

Communicates with backend via /api/initialize and /api/chat.
#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-#+-

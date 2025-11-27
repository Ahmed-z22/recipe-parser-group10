# recipe-parser-group10

A recipe parsing project — developed as part of **COMP SCI 337** at **Northwestern University**,
**Group 10**, *Fall 2025*.

&nbsp;

## Conda environment
>> conda env create -f environment.yml
>> conda activate recipe-parser-group10

&nbsp;

## Gemini API key
1. Create an API key from [Google AI Studio](https://aistudio.google.com/api-keys).
2. Put your API key in the next command
>> echo "GEMINI_API_KEY=PUT_YOUR_API_KEY_HERE" > apikey.env 

## Running the recipe parser (UI)

### Backend
Run the backend api in separate terminal:
>> python backend/api.py

Runs on **[http://localhost:5001](http://localhost:5001)**.

### Frontend
To setup and run the UI, open new terminal window and run the following commands
>> cd frontend/ 
>> npm install
>> npm start

Opens at **[http://localhost:3000](http://localhost:3000)**.
Backend must be running on port **5001**.

### Select a Processing Mode
- Classical NLP
- LLM (Gemini)
- Hybrid (NLP + LLM)
    - <span style="color:red; font-weight:bold">Hybrid mode may be very slow without a Gemini subscription — loading can take up to around 5 minutes</span>

### Steps
1. Enter a recipe URL from a supported website
    - allrecipes.com
    - epicurious.com
    - bonappetit.com
2. Click **Load Recipe**
3. Ask questions about the recipe
4. Explore the TTS feature!
5. Explore talking to the agent using the record button! (STT)

### Supported browsers
1. `Google Chroom`
2. `Safari`
3. `Firefox (only TTS is supported)`

### Recommended version
- node: >= `22.16.0`
- npm: >= `10.9.2`

&nbsp;

## Running the recipe parser (CLI)

### Classical NLP or Hybrid (NLP + LLM) modes
>> python -m src.chatbot

### LLM (Gemini) mode:
>> python -m src.LLM_based_qa

### Usage (CLI)
1. Choose the mode if applicable
2. Enter a recipe URL from a supported website
    - allrecipes.com
    - epicurious.com
    - bonappetit.com
3. Ask questions about the recipe

&nbsp;

## Allowed questions (Only for Classical NLP mode)
- **Please look at [`allowed_questions.txt`](allowed_questions.txt) to see some of the questions examples**

&nbsp;

## Project structure
```bash
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
│   │   ├── parameter_clarification_procedure_prompt.txt
│   │   ├── preparations_prompt.txt
│   │   ├── qa_prompt.txt
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
```

&nbsp;

## Note
**For a detailed overview of the project structure and source code descriptions, see** [`README.txt`](README.txt).

# recipe-parser-group10

A recipe parsing project — developed as part of **COMP SCI 337** at **Northwestern University**,
**Group 10**, *Fall 2025*.

&nbsp;

## Conda environment

>> conda env create -f environment.yml

>> conda activate recipe-parser-group10

&nbsp;

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

### Usage (UI)
1. Enter a supported recipe URL (allrecipes.com, epicurious.com, bonappetit.com)
2. Click **Load Recipe**
3. Ask questions about the recipe
4. Explore the TTS feature!
5. Explore talking to the agent using the record button! (STT)

### Supported websites
1. `Google Chroom`
2. `Safari`
3. `Firefox (only TTS is supported)`

### Recommended version
- node: >= `22.16.0`
- npm: >= `10.9.2`

&nbsp;

## Running the recipe parser (CLI)
In the CLI run the following command:
>> python -m src.chatbot

### Usage (CLI)
1. Enter a supported recipe URL (allrecipes.com, epicurious.com, bonappetit.com)
2. Ask questions about the recipe

&nbsp;

## Allowed questions
- **Please look at `allowed_questions.txt`**
- **Click here to go to the allowed_questions.txt file => [Allowed Questions](allowed_questions.txt)**

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
│   │   ├── tools_keywords.json
│   │   ├── unicode_fractions.json
│   │   └── units_map.json
│   ├── __init__.py
│   ├── chatbot.py
│   ├── ingredients_parser.py
│   ├── methods_parser.py
│   ├── scraper.py
│   ├── steps_parser.py
│   └── tools_parser.py
├── .gitignore
├── environment.yml
├── pyproject.toml
├── allowed_questions.txt
├── README.md
└── README.txt
```

&nbsp;

## Note
**For a detailed overview of the project structure and source code descriptions, see** [`README.txt`](README.txt).

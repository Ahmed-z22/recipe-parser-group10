import json
import re
import spacy
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
import os


class IngredientsParser:
    def __init__(self, ingredients: dict[str, list[str]], mode: str = "classical"):
        self.mode = mode

        if self.mode == "classical":
            self.ingredients = ingredients["ingredients"]
            self.ingredients_names = None
            self.ingredients_quantities_and_amounts = None
            self.ingredients_measurement_units = None
            self.descriptors = None
            self.preparations = None
            self.nlp = spacy.load("en_core_web_sm")
            self.path = Path(__file__).resolve().parent / "helper_files"
            self.alias_to_canon = self._load_json(self.path / "units_map.json")
            self.unicode_fractions = self._load_json(self.path / "unicode_fractions.json")
            self.frac_chars = "".join(self.unicode_fractions.keys())
            self.units_pattern = "|".join(
                sorted(map(re.escape, self.alias_to_canon.keys()), key=len, reverse=True)
            )
            self.qty = re.compile(
                r"^\s*(?:\d+(?:\.\d+)?\s*(?:-|–|to)\s*\d+(?:\.\d+)?|(?:(\d+)\s*)?["
                + re.escape(self.frac_chars)
                + r"]|(?:(\d+)\s+)?\d+\s*/\s*\d+|\d+\.\d+|\d+)\s*",
                re.I,
            )
            self.unit = re.compile(r"^\s*(?:" + self.units_pattern + r")\b\.?\s*", re.I)
            self.paren = re.compile(r"\([^)]*\)")
        else:
            self.path = Path(__file__).resolve().parent.parent
            load_dotenv(self.path / "apikey.env")
            self.api_key = os.getenv("GEMINI_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "GEMINI_API_KEY not found. Please set it in your .env file."
                )

            with open(self.path / "src" / "prompts" / "LLM_based_qa_prompt.txt", "r") as f:
                self.system_prompt = f.read()

            self.client = genai.Client()
            self.chat = self.client.chats.create(
                model=model_name,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    temperature=0.2,
                    top_p=0.8,
                    top_k=40,
                ),
            )


    def _load_json(self, path: Path) -> dict[str, str]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def extract_ingredients_names(self):
        """
        Extracts core ingredient names, and stores them in self.ingredients_names.
        """
        results = []
        for line in self.ingredients:
            match = self.qty.search(line)
            line = line[match.end() :] if match else line
            match = self.unit.search(line)
            line = line[match.end() :] if match else line
            line = self.paren.sub("", line)
            line = line.rsplit(",", 1)[0].strip()
            line = re.sub(r"\s+", " ", line).strip()

            doc = self.nlp(line)
            noun_chunks = list(doc.noun_chunks)
            if noun_chunks:
                chunk = noun_chunks[-1]
                head = chunk.root
                keep_tokens = []
                for tok in chunk:
                    if tok.dep_ == "compound":
                        keep_tokens.append(tok.text)
                    elif tok == head:
                        keep_tokens.append(tok.text)
                line = " ".join(keep_tokens).lower().strip()
            results.append(line)
        self.ingredients_names = results

    def extract_quantities(self):
        """
        Extracts the quantity value from each ingredient line.
        Stores the numeric results (or None if no quantity found) in
        self.ingredients_quantities_and_amounts.
        """
        amounts = re.compile(
            r"^\s*(?:(?P<r1>\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(?P<r2>\d+(?:\.\d+)?)|(?:(?P<uw>\d+)\s*)?(?P<uf>["
            + re.escape(self.frac_chars)
            + r"])|(?P<dec>\d+\.\d+)|(?P<int>\d+))",
            re.I,
        )

        results = []
        for line in self.ingredients:
            quantity = None
            match = amounts.search(line)
            if match:
                groups = match.group
                if groups("r1"):
                    quantity = float(groups("r1"))
                elif groups("uf"):
                    quantity = (float(groups("uw")) if groups("uw") else 0.0) + float(
                        self.unicode_fractions.get(groups("uf"), 0.0)
                    )
                elif groups("dec"):
                    quantity = float(groups("dec"))
                elif groups("int"):
                    quantity = float(groups("int"))

            if quantity is not None and quantity.is_integer():
                quantity = int(quantity)
            results.append(quantity)
        self.ingredients_quantities_and_amounts = results

    def extract_measurement_units(self):
        """
        Detects the measurement unit in each ingredient line.
        Stores the unit name (or None if no unit found) in self.ingredients_measurement_units.
        """
        units = re.compile(rf"\b({self.units_pattern})\b", re.I)

        results = []
        for line in self.ingredients:
            match = units.search(self.paren.sub(" ", line)) or units.search(line)
            results.append(
                self.alias_to_canon.get(match.group(1).lower()) if match else None
            )
        self.ingredients_measurement_units = results

    def extract_descriptors(self):
        """
        Extracts descriptive modifiers of the ingredient (adjectives, compounds, and participial adjectives)
        after removing quantities, units, and preparation phrases. And stores them in self.descriptors.
        """
        results = []
        for line in self.ingredients:
            match = self.qty.search(line)
            line = line[match.end() :] if match else line
            match = self.unit.search(line)
            line = line[match.end() :] if match else line
            line = self.paren.sub("", line)
            line = line.rsplit(",", 1)[0].strip()
            line = re.sub(r"\s+", " ", line).strip()

            doc = self.nlp(line)
            head = next((t for t in reversed(doc) if t.pos_ in ("NOUN", "PROPN")), None)
            if not head:
                results.append([])
                continue

            descriptors = []
            for tok in doc:
                if tok.dep_ == "amod" and tok.head == head:
                    descriptors.append(tok.text.lower())
                elif tok.dep_ == "compound" and tok.head == head:
                    descriptors.append(tok.text.lower())
                elif (
                    tok.tag_ in ("VBN", "VBG")
                    and tok.dep_ == "amod"
                    and tok.head == head
                ):
                    descriptors.append(tok.text.lower())
            results.append(descriptors)
        self.descriptors = results

    def extract_preparations(self):
        """
        Extract preparation notes by taking the text after the last comma, keeping it only if it contains a verb or participle.
        Stores the results in self.preparations.
        """
        results = []
        for line in self.ingredients:
            parts = line.rsplit(",", 1)
            line = parts[1].strip() if len(parts) > 1 else ""
            line = self.paren.sub("", line)
            line = re.sub(r"\s+", " ", line).strip()

            doc = self.nlp(line) if line else None
            keep = False
            if doc:
                for tok in doc:
                    if tok.pos_ == "VERB" or tok.tag_ in ("VBG", "VBN"):
                        keep = True
                        break
            results.append([line] if keep and line else [])
        self.preparations = results

    def parse(self) -> list[dict[str, list[str] | str | int | float | None]]:
        """ "
        Executes all extraction methods ingredients.
        returns: A list of dictionaries, each containing the parsed components of an ingredient:
            - original_ingredient_sentence: The original ingredient line.
            - ingredient_name: The extracted ingredient name (str).
            - ingredient_quantity: The extracted quantity (int, float, or None).
            - measurement_unit: The standardized measurement unit (str or None).
            - ingredient_preparation: List of preparation phrases (list of str).
            - ingredient_descriptors: List of adjective descriptors (list of str).
        """
        self.extract_ingredients_names()
        self.extract_quantities()
        self.extract_measurement_units()
        self.extract_descriptors()
        self.extract_preparations()

        output = []
        for i in range(len(self.ingredients)):
            output.append(
                {
                    "original_ingredient_sentence": self.ingredients[i],
                    "ingredient_name": self.ingredients_names[i],
                    "ingredient_quantity": self.ingredients_quantities_and_amounts[i],
                    "measurement_unit": self.ingredients_measurement_units[i],
                    "ingredient_descriptors": self.descriptors[i],
                    "ingredient_preparation": self.preparations[i],
                }
            )

        return output

import json
import re
import spacy
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
import os
import time


class IngredientsParser:
    def __init__(
        self,
        ingredients: dict[str, list[str]],
        mode: str = "classical",
        model_name: str = "gemini-2.5-flash-lite",
    ):
        self.mode = mode
        self.ingredients = ingredients["ingredients"]
        self.ingredients_names = None
        self.ingredients_quantities_and_amounts = None
        self.ingredients_measurement_units = None
        self.descriptors = None
        self.preparations = None
        self.model_name = model_name

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

        if self.mode != "classical":
            self.path = Path(__file__).resolve().parent.parent
            load_dotenv(self.path / "apikey.env")
            self.api_key = os.getenv("GEMINI_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "GEMINI_API_KEY not found. Please set it in your .env file."
                )

            self.client = genai.Client(api_key=self.api_key)

            self.ingredients_names_prompt = self._load_text(
                self.path / "src" / "prompts" / "ingredients_names_prompt.txt"
            )
            # self.quantities_prompt = self._load_text(
            #     self.path / "src" / "prompts" / "quantities_prompt.txt"
            # )
            # self.measurement_units_prompt = self._load_text(
            #     self.path / "src" / "prompts" / "measurement_units_prompt.txt"
            # )
            self.descriptors_prompt = self._load_text(
                self.path / "src" / "prompts" / "descriptors_prompt.txt"
            )
            self.preparations_prompt = self._load_text(
                self.path / "src" / "prompts" / "preparations_prompt.txt"
            )

            self.paren = re.compile(r"\([^)]*\)")

    def _load_text(self, path: Path) -> str:
        with path.open("r", encoding="utf-8") as f:
            return f.read()

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

    def _message_formatting(self, context: str) -> str:
        return "=== Context ===\n" f"{context}\n\n" "=== Context ===\n\n" "Output:"

    def _call_llm(self, task_prompt: str):
        """
        Calls the LLM with a given task prompt and the current ingredients list.
        Expects the model to return ONLY a JSON array (no extra text).
        """
        payload = json.dumps({"ingredients": self.ingredients}, ensure_ascii=False)
        full_prompt = task_prompt.strip() + "\n\nINPUT JSON:\n" + payload

        contents = self._message_formatting(full_prompt)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.2,
                top_p=0.8,
                top_k=40,
            ),
        )

        try:
            raw = response.text
        except AttributeError:
            raw_parts = []
            for cand in getattr(response, "candidates", []) or []:
                for part in getattr(cand, "content", {}).parts or []:
                    if hasattr(part, "text"):
                        raw_parts.append(part.text)
            raw = "".join(raw_parts)

        if raw is None:
            raise ValueError("LLM response had no text content.")

        text = raw.strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            if text.endswith("```"):
                text = text[:-3].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse LLM JSON output: {e}\nRaw output:\n{text}"
            ) from e

    def llm_based_extraction(self):
        """
        Uses the LLM (with 5 task-specific prompts) to populate:
        - self.ingredients_names
        - self.ingredients_quantities_and_amounts
        - self.ingredients_measurement_units
        - self.descriptors
        - self.preparations
        """

        try:
            self.ingredients_names = self._call_llm(self.ingredients_names_prompt)
            time.sleep(5)
        except Exception:
            self.extract_ingredients_names()  # Fallback to classical extraction
            time.sleep(20)

        # self.ingredients_quantities_and_amounts = self._call_llm(self.quantities_prompt)
        # self.ingredients_measurement_units = self._call_llm(self.measurement_units_prompt)
        self.extract_quantities()  # Regular extraction for quantities
        self.extract_measurement_units()  # Regular extraction for measurement units

        try:
            self.descriptors = self._call_llm(self.descriptors_prompt)
            time.sleep(5)
        except Exception:
            self.extract_descriptors()  # Fallback to classical extraction
            time.sleep(20)

        try:
            self.preparations = self._call_llm(self.preparations_prompt)
            time.sleep(5)
        except Exception:
            self.extract_preparations()  # Fallback to classical extraction
            time.sleep(20)

        n = len(self.ingredients)
        for name, arr in [
            ("ingredient_name", self.ingredients_names),
            ("ingredient_quantity", self.ingredients_quantities_and_amounts),
            ("measurement_unit", self.ingredients_measurement_units),
            ("ingredient_descriptors", self.descriptors),
            ("ingredient_preparation", self.preparations),
        ]:
            if not isinstance(arr, list) or len(arr) != n:
                raise ValueError(
                    f"LLM output for {name} must be a list of length {n}, got {type(arr)} with length {len(arr) if isinstance(arr, list) else 'N/A'}."
                )

    def _clean_name_with_descriptors(self, name: str, descriptors: list[str]) -> str:
        """
        Remove any token from ingredient_name that also appears in ingredient_descriptors.
        """
        if not name:
            return name

        name_tokens = name.split()
        desc_set = set(descriptors or [])

        cleaned = [tok for tok in name_tokens if tok not in desc_set]

        return " ".join(cleaned).strip()

    def _parse_classical(self) -> list[dict[str, list[str] | str | int | float | None]]:
        """
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

    def _parse_llm(self) -> list[dict[str, list[str] | str | int | float | None]]:
        """
        LLM-based parsing. Same output schema as _parse_classical.
        """

        self.llm_based_extraction()

        output = []
        for i in range(len(self.ingredients)):
            cleaned_name = self._clean_name_with_descriptors(
                self.ingredients_names[i], self.descriptors[i]
            )
            output.append(
                {
                    "original_ingredient_sentence": self.ingredients[i],
                    "ingredient_name": cleaned_name,
                    "ingredient_quantity": self.ingredients_quantities_and_amounts[i],
                    "measurement_unit": self.ingredients_measurement_units[i],
                    "ingredient_descriptors": self.descriptors[i],
                    "ingredient_preparation": self.preparations[i],
                }
            )
        return output

    def parse(self) -> list[dict[str, list[str] | str | int | float | None]]:
        """
        Parses the ingredients based on the selected mode.

        - "classical": spaCy-based pipeline only.
        - "hybrid": try LLM first; if it fails for any reason, fall back to classical.
        - anything else: treat as full LLM mode.
        """
        if self.mode == "classical":
            return self._parse_classical()
        else:
            return self._parse_llm()

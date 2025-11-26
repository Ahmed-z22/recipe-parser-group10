import json
import spacy
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
import os
import re


class MethodsParser:
    def __init__(self, directions, mode = "classical", model_name = "gemini-2.5-flash"):
        self.mode = mode
        self.model_name = model_name

        self.directions = directions["directions"]
        self.tools = None
        self.nlp = spacy.load("en_core_web_sm")
        self.directions_split = self.split_directions_into_steps()
        # Load method keywords from JSON file
        self.path = Path(__file__).resolve().parent / "helper_files"
        method_keywords_path = self.path / "method_keywords.json"
        with open(method_keywords_path, "r") as f:
            data = json.load(f)

        self.method_keywords = data.get("method_keywords")

        if self.mode != "classical":
            self.path = Path(__file__).resolve().parent.parent
            load_dotenv(self.path / "apikey.env")
            self.api_key = os.getenv("GEMINI_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "GEMINI_API_KEY not found. Please set it in your .env file."
                )

            self.client = genai.Client(api_key=self.api_key)

            with open(self.path / "src" / "prompts" / "methods_prompt.txt", "r") as f:
                self.methods_prompt = f.read()

    def split_directions_into_steps(self):
        """
        Split recipe directions into individual sentence steps.

        Processes each direction entry, breaks down each direction into
        individual sentences, creating a dictionary mapping original
        directions to their constituent sentence steps.

        Returns:
            dict: A dictionary where keys are original direction entries
             and values are lists of individual sentence steps.
        """
        # split_dirs = []
        split_dirs = {}
        for entry in self.directions:
            doc = self.nlp(entry)
            sents = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
            # split_dirs.extend(sents)
            split_dirs[entry] = sents
        return split_dirs

    def extract_methods(self, step):
        """Extracts tools from a given step using spaCy NLP.
        Args:
            step (str): A single step from the recipe directions.
        Returns:
            list: A list of extracted tools found in the step.
        """
        doc = self.nlp(step)
        methods = []

        # prefer ROOT verb, then first-token verb, then any other verb in sentence
        for tok in doc:
            is_verb_like = tok.pos_ == "VERB" or tok.tag_.startswith("VB")
            if not is_verb_like:
                continue
            if tok.lemma_.lower() in {"be", "have", "do", "get", "make"}:
                continue
            particle = " ".join(
                child.text for child in tok.children if child.dep_ == "prt"
            )
            verb_norm = (
                tok.lemma_.lower() + (" " + particle if particle else "")
            ).strip()

            if tok.dep_ == "ROOT":
                # add root verb
                methods.insert(0, verb_norm)
                # also add any conjoined verbs (e.g. "cook and stir")
                for conj in (
                    c
                    for c in doc
                    if c.head is tok
                    and c.dep_ == "conj"
                    and (c.pos_ == "VERB" or c.tag_.startswith("VB"))
                ):
                    particle_c = " ".join(
                        child.text for child in conj.children if child.dep_ == "prt"
                    )
                    methods.append(
                        (
                            conj.lemma_.lower()
                            + (" " + particle_c if particle_c else "")
                        ).strip()
                    )
                # don't break — allow other heuristics to collect verbs before/after
                continue

            # keep first-token verb (imperative) or verbs in whitelist
            if tok.i == 0 or tok.lemma_.lower() in self.method_keywords:
                methods.append(verb_norm)
                # also include any conjoined verbs of this token
                for conj in (
                    c
                    for c in doc
                    if c.head is tok
                    and c.dep_ == "conj"
                    and (c.pos_ == "VERB" or c.tag_.startswith("VB"))
                ):
                    particle_c = " ".join(
                        child.text for child in conj.children if child.dep_ == "prt"
                    )
                    methods.append(
                        (
                            conj.lemma_.lower()
                            + (" " + particle_c if particle_c else "")
                        ).strip()
                    )

        # fallback: if nothing found, try first token if verb-like
        if (
            not methods
            and len(doc)
            and (doc[0].pos_ == "VERB" or doc[0].tag_.startswith("VB"))
        ):
            methods.append(doc[0].lemma_.lower())

        # keep order, unique
        methods = list(dict.fromkeys(methods))

        # apply whitelist filter if provided
        if self.method_keywords:
            methods = [
                m
                for m in methods
                if any(m == k or m.startswith(k + " ") for k in self.method_keywords)
            ]

        return methods
    
    def _message_formatting(self, context: str) -> str:
        return (
            "=== Context ===\n"
            f"{context}\n\n"
            "=== Context ===\n\n"
            "Output:"
        )
    
    def extract_methods_llm(self, step):
        """Extracts tools from a given step using LLM-based approach.
        Args:
            step (str): A single step from the recipe directions.
        Returns:
            list: A list of extracted tools (methods) found in the step.
        """
        payload = json.dumps({"step": step}, ensure_ascii=False)
        full_prompt = self.methods_prompt.strip() + "\n\nINPUT JSON:\n" + payload

        contents = self._message_formatting(full_prompt)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.2,
                top_p=0.8,
                top_k=40,
            )
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
            return self.extract_methods(step)

        text = raw.strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            if text.endswith("```"):
                text = text[:-3].strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return self.extract_methods(step)

        if not isinstance(parsed, list):
            return self.extract_methods(step)

        methods = []
        for item in parsed:
            if isinstance(item, str):
                m = item.strip().lower()
                if m:
                    methods.append(m)

        return methods

    def parse(self, flag_llm=False):
        """
        Parse cooking directions and extract cooking methods from each step.
        Uses self.extract_methods() to identify cooking methods in each step.

        Returns:
            list[dict]: A list of dictionaries where each dictionary contains:
                - "direction" (str): The original direction text
                - "steps" (list): List of individual steps for this direction
                - "methods" (list): Unique cooking methods extracted from all steps in this direction
        """

        output = []

        for direction, steps in self.directions_split.items():
            output_dict = {"direction": direction, "steps": steps, "methods": ()}
            for step in steps:
                if flag_llm:
                    methods_in_step = self.extract_methods_llm(step)
                else:
                    methods_in_step = self.extract_methods(step)
                output_dict["methods"] = list(
                    set(output_dict["methods"]) | set(methods_in_step)
                )
            output.append(output_dict)

        return output

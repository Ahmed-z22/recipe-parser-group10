import json
import re
import spacy
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
import os
import re


class ToolsParser:
    def __init__(self, directions, mode="classical", model_name="gemini-2.5-flash"):
        self.mode = mode
        self.model_name = model_name

        self.directions = directions["directions"]
        self.tools = None
        self.nlp = spacy.load("en_core_web_sm")
        self.directions_split = self.split_directions_into_steps()
        self.path = Path(__file__).resolve().parent / "helper_files"
        tools_keywords_path = self.path / "tools_keywords.json"
        with open(tools_keywords_path, "r") as f:
            data = json.load(f)

        # small list — can be expanded with common kitchen tools
        self.tool_keywords = data.get("tools_keywords")

        # words that might indicate a tool is being used
        self.prep_word = data.get("prep_words")

        # verbs that often imply tool usage
        self.tool_verb_list = data.get("tool_verb_list")

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

            with open(self.path / "src" / "prompts" / "tools_prompt.txt", "r") as f:
                self.tools_prompt = f.read()

    # can maybe add this to the Steps section
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
        split_dirs = {}
        for entry in self.directions:
            doc = self.nlp(entry)
            sents = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
            # split_dirs.extend(sents)
            split_dirs[entry] = sents
        return split_dirs

    def extract_tools(self, text: str) -> list[str]:
        """
        Extract cooking tools and equipment from recipe text using natural language processing.
        Args:
            text (str): The recipe text
        Returns:
            list[str]: A sorted list of normalized tool names found in the text.
                       Duplicates are removed and articles (a, an, the) are stripped
                       from the beginning of tool names.
        Example:
            >>> parser.extract_tools("Heat oil in a large skillet and use a wooden spoon to stir")
            ['large skillet', 'wooden spoon']
        """

        doc = self.nlp(text)
        candidates = set()

        # first look for noun chunks that might indicate tools
        for chunk in doc.noun_chunks:
            tokens = list(chunk)
            kept = []
            for t in tokens:
                if (
                    t.pos_ == "ADP"
                    or t.dep_ == "prep"
                    or t.like_num
                    or t.text.lower() in self.prep_word
                    or t.text.lower() == "to"
                ):
                    break
                kept.append(t)
            if not kept:
                continue

            chunk_text = (
                " ".join(t.text for t in kept).lower().strip()
            )  # filter to token text
            chunk_text = re.sub(
                r"\([^)]*\)", "", chunk_text
            ).strip()  # remove parentheticals

            root = chunk.root
            if root.dep_ in {"pobj", "dobj", "pcomp", "attr", "dative"} or (
                root.left_edge.i > 0 and doc[root.left_edge.i - 1].pos_ == "ADP"
            ):
                if (root.head.lemma_.lower() in self.tool_verb_list) or (
                    doc[root.left_edge.i - 1].lemma_.lower() in self.prep_word
                ):
                    candidates.add(chunk_text)
                else:
                    if any(k in chunk_text for k in self.tool_keywords):
                        candidates.add(chunk_text)

        # fallback single-token matches to predefined list (keep left modifiers like "large")
        for tok in doc:
            if (
                tok.lemma_.lower() in self.tool_keywords
                or tok.text.lower() in self.tool_keywords
            ):
                if tok.pos_ in {"NOUN", "PROPN"} and (
                    tok.dep_ in {"dobj", "pobj", "attr", "ROOT", "conj"}
                    or tok.head.lemma_.lower() in self.tool_verb_list
                ):
                    left_mods = [
                        t for t in tok.lefts if t.dep_ in {"det", "amod", "compound"}
                    ]
                    span_text = " ".join(t.text for t in left_mods + [tok]).lower()
                    span_text = re.sub(r"\([^)]*\)", "", span_text).strip()
                    candidates.add(span_text)

        def norm(s):  # remove a, an, the
            return re.sub(r"^(a|an|the)\s+", "", s).strip()

        tools = sorted(
            {norm(c) for c in candidates if any(k in c for k in self.tool_keywords)}
        )
        return tools

    def _message_formatting(self, context: str) -> str:
        return "=== Context ===\n" f"{context}\n\n" "=== Context ===\n\n" "Output:"

    def extract_tools_llm(self, step):
        """
        Extract cooking tools and equipment from recipe text using llm-based approach.
        Args:
            step (str): A single step from the recipe directions.
        Returns:
            list[str]: A list of normalized tool names found in the text.
        Example:
            >>> parser.extract_tools_llm("Heat oil in a large skillet and use a wooden spoon to stir")
            ['large skillet', 'wooden spoon']
        """
        payload = json.dumps({"step": step}, ensure_ascii=False)
        full_prompt = self.tools_prompt.strip() + "\n\nINPUT JSON:\n" + payload

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
            return self.extract_tools(step)

        text = raw.strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            if text.endswith("```"):
                text = text[:-3].strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return self.extract_tools(step)

        if not isinstance(parsed, list):
            return self.extract_tools(step)

        tools = []
        for item in parsed:
            if isinstance(item, str):
                t = item.strip().lower()
                if t:
                    tools.append(t)

        return tools

    def parse(self, flag_llm=False):
        """
        Parse directions and extract tools used in each direction's steps.
        Relies on the extract_tools() method to identify tools from step text.

        Returns:
            list: A list of dictionaries, each containing:
                - 'direction' (str): The original direction identifier or name
                - 'steps' (list): List of step descriptions for this direction
                - 'tools' (list): Unique tools extracted from all steps in this direction
        """

        output = []

        for direction, steps in self.directions_split.items():
            output_dict = {"direction": direction, "steps": steps, "tools": ()}
            for step in steps:
                if flag_llm:
                    tools_in_step = self.extract_tools_llm(step)
                else:
                    tools_in_step = self.extract_tools(step)
                output_dict["tools"] = list(
                    set(output_dict["tools"]) | set(tools_in_step)
                )
            output.append(output_dict)

        return output

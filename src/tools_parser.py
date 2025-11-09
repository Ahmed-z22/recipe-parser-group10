import json, re, spacy
from pathlib import Path

class ToolsParser:
    def __init__(self, directions):
        self.directions = directions['directions']
        self.tools = None
        self.nlp = spacy.load("en_core_web_sm")
        self.directions_split = self.split_directions_into_steps()
        # small list — can be expanded with common kitchen tools
        self.tool_keywords = {"pot","pan","skillet","bowl","oven","lid","sheet","saucepan",
                                "colander","knife","spoon","fork","blender","mixer","grill","tray",
                                "griddle", "scoop", "whisk", "peeler", "rolling pin", "measuring cup",
                                "measuring spoon", "strainer", "cutting board", "tongs", "spatula"
                            }
        # words that might indicate a tool is being used
        self.prep_word = {"in","into","on","over","using","with","onto"}
        # verbs that often imply tool usage
        self.tool_verb_list = {"use","place","put","heat","preheat","cook","bake","stir","whisk","pour","simmer"}


    # can maybe add this to the Steps section
    # this function splits directions into single steps based on sentences. So each sentence is a step.
    def split_directions_into_steps(self):
        split_dirs = []
        for entry in self.directions:
            doc = self.nlp(entry)
            sents = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
            split_dirs.extend(sents)
        return split_dirs


    def extract_tools(self, text: str) -> list[str]:
        """
        Extracts kitchen tools from a given direction text.
        """

        doc = self.nlp(text)
        candidates = set()

        # first look for noun chunks that might indicate tools
        for chunk in doc.noun_chunks:
            tokens = list(chunk)
            kept = []
            for t in tokens:
                if t.pos_ == "ADP" or t.dep_ == "prep" or t.like_num or t.text.lower() in self.prep_word or t.text.lower() == "to":
                    break
                kept.append(t)
            if not kept:
                continue

            chunk_text = " ".join(t.text for t in kept).lower().strip() # filter to token text
            chunk_text = re.sub(r"\([^)]*\)", "", chunk_text).strip() # remove parentheticals

            root = chunk.root
            if (root.dep_ in {"pobj", "dobj", "pcomp", "attr", "dative"} or
                (root.left_edge.i > 0 and doc[root.left_edge.i - 1].pos_ == "ADP")):
                if (root.head.lemma_.lower() in self.tool_verb_list) or (doc[root.left_edge.i - 1].lemma_.lower() in self.prep_word):
                    candidates.add(chunk_text)
                else:
                    if any(k in chunk_text for k in self.tool_keywords):
                        candidates.add(chunk_text)

        # fallback single-token matches to predefined list (keep left modifiers like "large")
        for tok in doc:
            if tok.lemma_.lower() in self.tool_keywords or tok.text.lower() in self.tool_keywords:
                if tok.pos_ in {"NOUN", "PROPN"} and (tok.dep_ in {"dobj", "pobj", "attr", "ROOT", "conj"} or tok.head.lemma_.lower() in self.tool_verb_list):
                    left_mods = [t for t in tok.lefts if t.dep_ in {"det", "amod", "compound"}]
                    span_text = " ".join(t.text for t in left_mods + [tok]).lower()
                    span_text = re.sub(r"\([^)]*\)", "", span_text).strip()
                    candidates.add(span_text)

        def norm(s): # remove a, an, the 
            return re.sub(r'^(a|an|the)\s+', '', s).strip()

        tools = sorted({norm(c) for c in candidates if any(k in c for k in self.tool_keywords)})
        return tools

    def parse(self): 
        """Parses the directions to extract tools used in the recipe.
        Returns: A list of dictionaries with extracted tools for each step.
        """
        output = []
        for step in self.directions_split:
            # print("Processing step:", step)
            tools_in_step = self.extract_tools(step)
            output.append({
                "step": step,
                "tools": tools_in_step
            })

        return output

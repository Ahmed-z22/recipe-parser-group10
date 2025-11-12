import json, re, spacy
from pathlib import Path

class ToolsParser:
    def __init__(self, directions):
        self.directions = directions['directions']
        self.tools = None
        self.nlp = spacy.load("en_core_web_sm")
        self.directions_split = self.split_directions_into_steps()
        tools_keywords_path = 'src/helper_files/tools_keywords.json'
        with open(tools_keywords_path, 'r') as f:
            data = json.load(f) 

        # small list — can be expanded with common kitchen tools
        self.tool_keywords = data.get('tools_keywords')

        # words that might indicate a tool is being used
        self.prep_word = data.get('prep_words')

        # verbs that often imply tool usage
        self.tool_verb_list = data.get('tool_verb_list')

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

        for direction, steps in self.directions_split.items():
            output_dict = {"direction": direction, "steps": steps, "tools": ()}
            for step in steps:
                tools_in_step = self.extract_tools(step)
                # output_dict["tools"].append(tools_in_step)
                output_dict["tools"] = list(set(output_dict["tools"]) | set(tools_in_step))
            output.append(output_dict)
                
        return output

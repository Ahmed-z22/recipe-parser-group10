import json, re, spacy
from pathlib import Path

class MethodsParser:
    def __init__(self, directions):
        self.directions = directions['directions']
        self.tools = None
        self.nlp = spacy.load("en_core_web_sm")
        self.directions_split = self.split_directions_into_steps()
        # small list — can be expanded with common kitchen tools
        self.method_keywords = method_keywords = {"bake", "boil", "drain", "chop", "fry", "grill", "mix", "roast", "saute", "steam", "whisk", "blend",
                                "slice", "dice", "knead", "marinate","poach", "broil", "simmer", "stir", "toast", "peel", "pour","sift","gather",
                                "sift","mix","stir","add", "whisk","sprinkle", "cook","bake","preheat","whisk","fold","sear", 
                           "chop","slice","dice","fry","saute","boil","simmer","roast","blend","layer", "cover", "uncover"
                           "knead","marinate","grill","steam","toast","pour","beat","season", "flip", "cook","scoop","heat", "cool", "cover"}


    # can maybe add this to the Steps section
    # this function splits directions into single steps based on sentences. So each sentence is a step.
    def split_directions_into_steps(self):
        split_dirs = []
        for entry in self.directions:
            doc = self.nlp(entry)
            sents = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
            split_dirs.extend(sents)
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
            particle = " ".join(child.text for child in tok.children if child.dep_ == "prt")
            verb_norm = (tok.lemma_.lower() + (" " + particle if particle else "")).strip()

            if tok.dep_ == "ROOT":
                # add root verb
                methods.insert(0, verb_norm)
                # also add any conjoined verbs (e.g. "cook and stir")
                for conj in (c for c in doc if c.head is tok and c.dep_ == "conj" and (c.pos_ == "VERB" or c.tag_.startswith("VB"))):
                    particle_c = " ".join(child.text for child in conj.children if child.dep_ == "prt")
                    methods.append((conj.lemma_.lower() + (" " + particle_c if particle_c else "")).strip())
                # don't break — allow other heuristics to collect verbs before/after
                continue

            # keep first-token verb (imperative) or verbs in whitelist
            if tok.i == 0 or tok.lemma_.lower() in self.method_keywords:
                methods.append(verb_norm)
                # also include any conjoined verbs of this token
                for conj in (c for c in doc if c.head is tok and c.dep_ == "conj" and (c.pos_ == "VERB" or c.tag_.startswith("VB"))):
                    particle_c = " ".join(child.text for child in conj.children if child.dep_ == "prt")
                    methods.append((conj.lemma_.lower() + (" " + particle_c if particle_c else "")).strip())

        # fallback: if nothing found, try first token if verb-like
        if not methods and len(doc) and (doc[0].pos_ == "VERB" or doc[0].tag_.startswith("VB")):
            methods.append(doc[0].lemma_.lower())

        # keep order, unique
        methods = list(dict.fromkeys(methods))

        # apply whitelist filter if provided
        if self.method_keywords:
            methods = [m for m in methods if any(m == k or m.startswith(k + " ") for k in self.method_keywords)]

        return methods

    

    def parse(self): 
        """Parses the directions to extract tools used in the recipe.
        Returns: A list of dictionaries with extracted tools for each step.
        """
        output = []
        for step in self.directions_split:
            # print("Processing step:", step)
            tools_in_step = self.extract_methods(step)
            output.append({
                "step": step,
                "tools": tools_in_step
            })

        return output

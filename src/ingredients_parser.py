import json
import re
from pathlib import Path
import spacy

class IngredientsParser:
    def __init__(self, ingredients):
        self.ingredients = ingredients['ingredients']
        self.ingredients_names = None
        self.ingredients_quantities_and_amounts = None
        self.ingredients_measurement_units = None
        self.descriptors = None
        self.preparations = None

        self.nlp = spacy.load("en_core_web_sm")

        self.base_dir = Path(__file__).resolve().parent
        self.units_file = self.base_dir / "helper_files" / "units_map.json"
        self.fractions_file = self.base_dir / "helper_files" / "unicode_fractions.json"

        with self.units_file.open("r", encoding="utf-8") as f:
            self.alias_to_canon = json.load(f)

        with self.fractions_file.open("r", encoding="utf-8") as f:
            self.unicode_fractions = json.load(f)
        
        self.frac_chars = "".join(self.unicode_fractions.keys())

    def extract_ingredients_names(self):
        """
        Extracts ingredient names by removing leading quantities, units, an optional
        leading "of", and any text after a comma. Normalizes whitespace and stores
        results in self.ingredients_names.
        """
        qty = re.compile(
            r"^\s*(?:\d+(?:\.\d+)?\s*(?:-|–|to)\s*\d+(?:\.\d+)?|(?:(\d+)\s*)?[" + re.escape(self.frac_chars) +
            r"]|(?:(\d+)\s+)?\d+\s*/\s*\d+|\d+\.\d+|\d+)\s*", re.I)
        unit = re.compile(
            r"^\s*(?:" + "|".join(sorted(map(re.escape, self.alias_to_canon.keys()), key=len, reverse=True)) +
            r")\b\.?\s*", re.I)
        of = re.compile(r"^\s*of\b\.?\s*", re.I)

        out = []
        for line in self.ingredients:
            match = qty.search(line);  line = line[match.end():] if match else line
            match = unit.search(line); line = line[match.end():] if match else line
            match = of.search(line);   line = line[match.end():] if match else line
            line = line.split(',', 1)[0]
            line = re.sub(r"\s+", " ", line).strip()
            out.append(line)
        self.ingredients_names = out

    def extract_quantities(self):
        """
        Extracts the quantity value from each ingredient line.
        Stores the numeric results (or None if no quantity found) in
        self.ingredients_quantities_and_amounts.
        """
        qty_re = re.compile(
            r"""^\s*(?:
                (?P<r1>\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(?P<r2>\d+(?:\.\d+)?) |
                (?:(?P<uw>\d+)\s*)?(?P<uf>[{f}]) |
                (?:(?P<aw>\d+)\s+)?(?P<num>\d+)\s*/\s*(?P<den>\d+) |
                (?P<dec>\d+\.\d+) |
                (?P<int>\d+)
            )""".format(f=re.escape(self.frac_chars)),
            re.VERBOSE | re.IGNORECASE)

        out = []
        for line in self.ingredients:
            quantity = None
            match = qty_re.search(line)
            if match:
                groups = match.group
                if groups('r1'):
                    quantity = float(groups('r1'))
                elif groups('uf'):
                    quantity = (float(groups('uw')) if groups('uw') else 0.0) + float(self.unicode_fractions.get(groups('uf'), 0.0))
                elif groups('num'):
                    denominator = int(groups('den'))
                    if denominator:
                        quantity = (float(groups('aw')) if groups('aw') else 0.0) + int(groups('num')) / denominator
                elif groups('dec'):
                    quantity = float(groups('dec'))
                elif groups('int'):
                    quantity = float(groups('int'))

            if quantity is not None and float(quantity).is_integer():
                quantity = int(quantity)
            out.append(quantity)
        self.ingredients_quantities_and_amounts = out

    def extract_measurement_units(self):
        """
        Detects the measurement unit in each ingredient line.
        Stores the unit name (or None if no unit found) in self.ingredients_measurement_units.
        """
        units_pattern = "|".join(sorted(map(re.escape, self.alias_to_canon), key=len, reverse=True))
        regex_units = re.compile(rf"\b({units_pattern})\b", re.IGNORECASE)
        regex_parent = re.compile(r"\([^)]*\)")

        out = []
        for line in self.ingredients:
            match = regex_units.search(regex_parent.sub(" ", line)) or regex_units.search(line)
            out.append(self.alias_to_canon.get(match.group(1).lower()) if match else None)
        self.ingredients_measurement_units = out

    def extract_descriptors(self):
        """
        Extracts adjective descriptors that modify the main ingredient noun in each line.
        Hyphenated adjective sequences are merged, and results are stored in `self.descriptors`.
        """
        results = []
        for line in self.ingredients:
            doc = self.nlp(line)
            head = next((t for t in reversed(doc) if t.pos_ in ("NOUN", "PROPN")), None)
            if not head:
                results.append([])
                continue

            chain = {head.i} | {t.i for t in doc if t.dep_ == "compound" and t.head == head}
            cand = [t for t in doc if t.pos_ == "ADJ" and t.dep_ == "amod" and t.head.i in chain]
            cand.sort(key=lambda t: t.i)

            out, i = [], 0
            while i < len(cand):
                j, phrase = i, cand[i].text
                while j + 1 < len(cand) and cand[j+1].i == cand[j].i + 2 and doc[cand[j].i + 1].text == "-":
                    phrase += "-" + cand[j+1].text
                    j += 1
                out.append(phrase.lower().strip(",.;:"))
                i = j + 1
            results.append(out)
        self.descriptors = results

    def extract_preparations(self):
        """
        Extracts preparation phrases (e.g., “thinly sliced”, “finely chopped”) associated
        with each ingredient by identifying participles and verbal modifiers linked to the
        ingredient’s main noun. Results are stored in `self.preparations`.
        """
        results = []
        for line in self.ingredients:
            doc = self.nlp(line)
            head = next((t for t in reversed(doc) if t.pos_ in ("NOUN","PROPN")), None)
            if not head:
                results.append([]); continue

            anchors = []
            anchors += [("amod", c) for c in head.children if c.dep_=="amod" and c.tag_ in ("VBN","VBG")]
            anchors += [("verb", c) for c in head.children if c.dep_ in ("acl","acl:relcl") and (c.pos_=="VERB" or c.tag_ in ("VBN","VBG"))]
            for tok in doc:
                if (tok.pos_=="VERB" or tok.tag_ in ("VBN","VBG")) and head.i in {t.i for t in tok.subtree} and {c.dep_ for c in tok.children} & {"nsubj","nsubjpass","obj","dobj"}:
                    anchors.append(("verb", tok))
            anchors += [(k, c) for k, v in list(anchors) for c in v.children if c.dep_=="conj" and (c.pos_=="VERB" or c.tag_ in ("VBN","VBG"))]

            spans = []
            for kind, v in anchors:
                left = v.i
                i = v.i - 1
                while i >= 0 and doc[i].dep_=="advmod" and not doc[i].is_punct and i == left - 1:
                    left = i; i -= 1
                if kind == "amod":
                    s, e = left, v.i
                else:
                    right = v.right_edge.i
                    e = next((j-1 for j in range(v.i+1, right+1) if doc[j].text==","), right)
                    s = left
                while s <= e and doc[s].is_punct: s += 1
                while e >= s and doc[e].is_punct: e -= 1
                if s <= e: spans.append((s, e))

            merged = []
            for s, e in sorted(spans):
                if not merged or s > merged[-1][1]: merged.append([s, e])
                else: merged[-1][1] = max(merged[-1][1], e)

            seen, preps = set(), []
            for s, e in merged:
                txt = " ".join(doc[s:e+1].text.split()).strip(" ,;")
                if txt and txt not in seen:
                    seen.add(txt); preps.append(txt)
            results.append(preps)
        self.preparations = results

    def parse(self):
        """"
        Executes all extraction methods to parse the ingredients.
        """
        self.extract_ingredients_names()
        self.extract_quantities()
        self.extract_measurement_units()
        self.extract_descriptors()
        self.extract_preparations()

    def answers(self):
        output = []
        for i in range(len(self.ingredients)):
            output.append({
                "original_ingredient_sentence": self.ingredients[i],
                "ingredient_quantity": self.ingredients_quantities_and_amounts[i],
                "measurement_unit": self.ingredients_measurement_units[i],
                "ingredient_preparation": self.preparations[i],
                "ingredient_descriptors": self.descriptors[i]
            })
        return output

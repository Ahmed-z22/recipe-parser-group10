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

    def extract_ingredients_names(self):
        frac_chars = "".join(self.unicode_fractions.keys())

        # Leading “noise” words we want to ignore so quantities/units can be matched
        re_noise = re.compile(
            r"^\s*(?:plus|and|with|about|approximately|approx\.|around|roughly|nearly|another|extra|more)\b[\s,]*",
            re.IGNORECASE,
        )

        # Leading quantity patterns (anchored at start)
        re_range   = re.compile(r"^\s*\d+(?:\.\d+)?\s*(?:-|–|to)\s*\d+(?:\.\d+)?\s*", re.IGNORECASE)
        re_unicode = re.compile(rf"^\s*(?:(\d+)\s*)?[{re.escape(frac_chars)}]\s*")
        re_ascii   = re.compile(r"^\s*(?:(\d+)\s+)?\d+\s*/\s*\d+\s*")
        re_decimal = re.compile(r"^\s*\d+\.\d+\s*")
        re_integer = re.compile(r"^\s*\d+\s*")

        # Parenthetical blocks following qty
        re_paren   = re.compile(r"^\s*\([^)]*\)\s*")

        # Unit tokens (longest first)
        units_pattern = "|".join(sorted((re.escape(k) for k in self.alias_to_canon.keys()), key=len, reverse=True))
        re_unit = re.compile(rf"^\s*(?:{units_pattern})\b\.?\s*", re.IGNORECASE)

        # Optional "of" after unit
        re_of = re.compile(r"^\s*of\b\s*", re.IGNORECASE)

        names = []
        for line in self.ingredients:
            s = line

            # 0) Strip leading noise words like "plus", "with", "about", etc.
            #    Loop in case there are multiple (e.g., "plus about 3 tbsp ...")
            for _ in range(3):
                m = re_noise.search(s)
                if m is not None:
                    s = s[m.end():]
                else:
                    break

            # 1) Strip leading quantity (try each pattern once)
            m = re_range.search(s)
            if m is not None:
                s = s[m.end():]
            else:
                m = re_unicode.search(s)
                if m is not None:
                    s = s[m.end():]
                else:
                    m = re_ascii.search(s)
                    if m is not None:
                        s = s[m.end():]
                    else:
                        m = re_decimal.search(s)
                        if m is not None:
                            s = s[m.end():]
                        else:
                            m = re_integer.search(s)
                            if m is not None:
                                s = s[m.end():]

            # 2) Remove immediate parenthetical blocks like "(28 ounce)"
            for _ in range(3):
                m = re_paren.search(s)
                if m is not None:
                    s = s[m.end():]
                else:
                    break

            # 3) Remove a single leading unit if present
            m = re_unit.search(s)
            if m is not None:
                s = s[m.end():]

            # 4) Optional "of"
            m = re_of.search(s)
            if m is not None:
                s = s[m.end():]

            # 5) Truncate at the first comma (drop prep notes)
            comma_idx = s.find(',')
            if comma_idx != -1:
                s = s[:comma_idx]

            s = re.sub(r"\s+", " ", s).strip()

            if not s:
                s = line.strip()

            names.append(s)

        self.ingredients_names = names

    def extract_quantities(self):

        frac_chars = "".join(self.unicode_fractions.keys())

        re_range   = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
        re_unicode = re.compile(rf"^\s*(?:(\d+)\s*)?([{re.escape(frac_chars)}])")
        re_ascii   = re.compile(r"^\s*(?:(\d+)\s+)?(\d+)\s*/\s*(\d+)")
        re_decimal = re.compile(r"^\s*(\d+\.\d+)")
        re_integer = re.compile(r"^\s*(\d+)")

        out = []
        for line in self.ingredients:
            qty = None

            m = re_range.search(line)
            if m:
                try:
                    qty = float(m.group(1))
                except:
                    qty = None

            if qty is None:
                m = re_unicode.search(line)
                if m:
                    whole = float(m.group(1)) if m.group(1) else 0.0
                    frac_val = self.unicode_fractions.get(m.group(2), 0.0)
                    qty = whole + float(frac_val)

            if qty is None:
                m = re_ascii.search(line)
                if m:
                    try:
                        whole = float(m.group(1)) if m.group(1) else 0.0
                        num, den = int(m.group(2)), int(m.group(3))
                        if den != 0:
                            qty = whole + (num / den)
                    except:
                        qty = None

            if qty is None:
                m = re_decimal.search(line)
                if m:
                    qty = float(m.group(1))

            if qty is None:
                m = re_integer.search(line)
                if m:
                    qty = float(m.group(1))

            if qty is not None and qty.is_integer():
                qty = int(qty)

            out.append(qty)

        self.ingredients_quantities_and_amounts = out

    def extract_measurement_units(self):

        units_pattern = "|".join(sorted((re.escape(k) for k in self.alias_to_canon.keys()), key=len, reverse=True))
        regex_units = re.compile(rf"\b({units_pattern})\b", re.IGNORECASE)

        regex_parent = re.compile(r"\([^)]*\)")

        out = []
        for line in self.ingredients:
            tmp = regex_parent.sub(" ", line)
            m = regex_units.search(tmp)

            unit = None
            if m:
                unit = self.alias_to_canon.get(m.group(1).lower())
            else:
                m2 = regex_units.search(line)
                if m2:
                    unit = self.alias_to_canon.get(m2.group(1).lower())

            out.append(unit)

        self.ingredients_measurement_units = out

    def _core_span_from_name(self, line: str, doc, core_name: str):
        # Try to locate the cleaned ingredient name inside the raw line
        i = line.lower().find(core_name.lower())
        if i == -1:
            return None  # fallback: no span found
        span = doc.char_span(i, i + len(core_name), alignment_mode="expand")
        return span  # may be None if alignment fails

    def _rightmost_noun(self, doc):
        nouns = [t for t in doc if t.pos_ in ("NOUN", "PROPN")]
        return nouns[-1] if nouns else None

    def extract_descriptor(self):
        stop_adj = {"other", "such", "additional", "more", "another"}

        results = []
        for line in self.ingredients:
            doc = self.nlp(line)
            head = self._rightmost_noun(doc)
            if head is None:
                results.append([])
                continue

            # collect the noun chain pointing into the head: rice <- grain <- (mods)
            chain = {head.i}
            for tok in doc:
                if tok.dep_ == "compound" and tok.head == head:
                    chain.add(tok.i)

            # adjectives directly modifying head
            cand = []
            for tok in doc:
                # keep only adjectives (JJ/JJR/JJS) that modify the head or a noun in the chain
                if tok.pos_ == "ADJ" and tok.dep_ == "amod" and (tok.head.i in chain):
                    # exclude trivial adjectives like "other"
                    if tok.lemma_.lower() not in stop_adj:
                        cand.append(tok)

            # join hyphenated multi-token adj like "extra - virgin" if spaCy split it
            cand = sorted(cand, key=lambda t: t.i)
            out = []
            i = 0
            while i < len(cand):
                j = i
                phrase = cand[i].text
                # grab immediate hyphen + next ADJ if present
                while j + 1 < len(cand) and cand[j+1].i == cand[j].i + 2 and doc[cand[j].i + 1].text == "-":
                    phrase += "-" + cand[j+1].text
                    j += 1
                out.append(phrase.lower().strip(",.;:"))
                i = j + 1

            results.append(out)

        self.descriptors = results
        return results

    def extract_preparations(self):
        """
        Generic, no-preprocessing preparation extractor.
        Anchors = VERB/VBN/VBG only.
        - amod participles → [adjacent ADV]* + participle   (e.g., "thinly sliced")
        - verbs/rel clauses/governing verbs → include right edge, clip at commas
        - whitelisted serving PPs (short): "for drizzling/serving", "to taste", "at room temperature"
        """

        def rightmost_noun(doc):
            ns = [t for t in doc if t.pos_ in ("NOUN","PROPN")]
            return ns[-1] if ns else None

        PP_WHITELIST = {
            ("for", "drizzling"),
            ("for", "serving"),
            ("to", "taste"),
            ("at", "room"),       
            ("at", "temperature"),
        }

        results = []

        for line in self.ingredients:
            doc = self.nlp(line)
            head = rightmost_noun(doc)
            if head is None:
                results.append([])
                continue

            anchors = []

            # 1) amod participles directly on the head: "thinly sliced cucumbers"
            for tok in head.children:
                if tok.dep_ == "amod" and tok.tag_ in ("VBN", "VBG"):
                    anchors.append(("amod_part", tok))

            # 2) verbal/relative clauses attached to head: "fillet, cut into cubes"
            for tok in head.children:
                if tok.dep_ in ("acl", "acl:relcl") and (tok.pos_ == "VERB" or tok.tag_ in ("VBN","VBG")):
                    anchors.append(("verb_span", tok))

            # 3) verbs/participles governing the head (e.g., "cucumbers, thinly sliced")
            for tok in doc:
                if not (tok.pos_ == "VERB" or tok.tag_ in ("VBN","VBG")):
                    continue
                if head.i in {t.i for t in tok.subtree}:
                    roles = {c.dep_ for c in tok.children}
                    if roles & {"nsubj","nsubjpass","obj","dobj"}:
                        anchors.append(("verb_span", tok))

            # 4) include coordinated prep verbs (peeled, seeded, and diced)
            expanded = list(anchors)
            for typ, v in anchors:
                for c in v.children:
                    if c.dep_ == "conj" and (c.pos_ == "VERB" or c.tag_ in ("VBN","VBG")):
                        expanded.append((typ, c))
            anchors = expanded

            spans = []

            for typ, v in anchors:
                if typ == "amod_part":
                    # include ADVs immediately adjacent on the left (to keep "thinly")
                    left = v.i
                    i = v.i - 1
                    while i >= 0 and doc[i].dep_ == "advmod" and not doc[i].is_punct and doc[i].i == left - 1:
                        left = i
                        i -= 1
                    s, e = left, v.i
                else:
                    # verb span: allow adjacent left adverbs, but never jump over commas
                    left = v.i
                    i = v.i - 1
                    while i >= 0 and doc[i].dep_ == "advmod" and not doc[i].is_punct and doc[i].i == left - 1:
                        left = i
                        i -= 1
                    s = left
                    # go to right edge, but clip at first comma after the verb
                    right = v.right_edge.i
                    # find first comma to the right of the verb token
                    comma_i = None
                    for j in range(v.i + 1, right + 1):
                        if doc[j].text == ",":
                            comma_i = j
                            break
                    e = (comma_i - 1) if comma_i is not None else right

                # trim leading/trailing punctuation
                while s <= e and doc[s].is_punct:
                    s += 1
                while e >= s and doc[e].is_punct:
                    e -= 1
                if s <= e:
                    spans.append((s, e))

            # 5) short serving PPs from the head: "for drizzling", "to taste", "at room temperature"
            for child in head.children:
                if child.dep_ == "prep":
                    subtree = [t for t in child.subtree if not t.is_punct]
                    if not subtree:
                        continue
                    words = [t.lemma_.lower() for t in subtree]
                    pairs = set()
                    if len(words) >= 2:
                        pairs.add((words[0], words[1]))
                    if len(words) >= 3:
                        pairs.add((words[0], words[-1]))  # "at ... temperature"
                    if PP_WHITELIST & pairs:
                        # ensure "at room temperature" completes
                        if words[0] == "at" and words[-1] != "temperature":
                            continue
                        s = min(t.i for t in subtree)
                        e = max(t.i for t in subtree)
                        spans.append((s, e))

            # 6) merge only if spans actually overlap and NOT across commas
            spans.sort()
            merged = []
            for s, e in spans:
                if not merged or s > merged[-1][1]:
                    merged.append([s, e])
                else:
                    merged[-1][1] = max(merged[-1][1], e)

            # 7) render
            out, seen = [], set()
            for s, e in merged:
                txt = " ".join(doc[s:e+1].text.split()).strip(" ,;")
                if txt and txt not in seen:
                    seen.add(txt)
                    out.append(txt)

            results.append(out)

        self.preparations = results

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

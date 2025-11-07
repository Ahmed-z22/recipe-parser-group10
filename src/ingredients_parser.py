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
        self.preparation = None

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

    def extract_measurement_unit(self):

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

    def extract_descriptor(self):
        # --- front-end cleanup (match your class style) ---
        frac_chars = "".join(self.unicode_fractions.keys())
        re_noise   = re.compile(r"^\s*(?:plus|and|with|about|approximately|approx\.|around|roughly|nearly|another|extra|more)\b[\s,]*", re.IGNORECASE)
        re_range   = re.compile(r"^\s*\d+(?:\.\d+)?\s*(?:-|–|to)\s*\d+(?:\.\d+)?\s*", re.IGNORECASE)
        re_unicode = re.compile(rf"^\s*(?:(\d+)\s*)?[{re.escape(frac_chars)}]\s*")
        re_ascii   = re.compile(r"^\s*(?:(\d+)\s+)?\d+\s*/\s*\d+\s*")
        re_decimal = re.compile(r"^\s*\d+\.\d+\s*")
        re_integer = re.compile(r"^\s*\d+\s*")
        re_paren   = re.compile(r"\([^)]*\)")
        units_pattern = "|".join(sorted((re.escape(k) for k in self.alias_to_canon.keys()), key=len, reverse=True))
        re_leading_unit = re.compile(rf"^\s*(?:{units_pattern})\b\.?\s*", re.IGNORECASE)
        re_of     = re.compile(r"^\s*of\b\s*", re.IGNORECASE)

        # words we don't want as descriptors
        drop_adj = {"other", "another", "such", "several", "many", "few", "additional", "more"}

        # allow prepositions in special hyphen forms like skin-on / bone-in / skin-off
        hyphen_right_allow = {"on", "in", "off"}

        descriptors_out = []

        for line in self.ingredients:
            s = line

            # strip leading noise
            for _ in range(3):
                m = re_noise.match(s)
                if m: s = s[m.end():]
                else: break

            # strip a single leading quantity
            m = re_range.match(s)
            if m: s = s[m.end():]
            else:
                m = re_unicode.match(s)
                if m: s = s[m.end():]
                else:
                    m = re_ascii.match(s)
                    if m: s = s[m.end():]
                    else:
                        m = re_decimal.match(s)
                        if m: s = s[m.end():]
                        else:
                            m = re_integer.match(s)
                            if m: s = s[m.end():]

            # remove all parentheticals anywhere
            s = re_paren.sub(" ", s)

            # remove a single leading unit if present
            m = re_leading_unit.match(s)
            if m: s = s[m.end():]

            # optional "of" right after unit
            m = re_of.match(s)
            if m: s = s[m.end():]

            s = re.sub(r"\s+", " ", s).strip()
            if not s:
                descriptors_out.append(None)
                continue

            # --- spaCy parse full line ---
            doc = self.nlp(s)

            found = []

            # 1) true adjectival modifiers ("amod") for any noun head
            for token in doc:
                if token.pos_ == "NOUN":
                    for left in token.lefts:
                        if left.dep_ == "amod" and left.pos_ == "ADJ":
                            txt = left.text.lower()
                            if txt not in drop_adj:
                                found.append((left.i, txt))

            # 2) hyphenated descriptors immediately left of a noun
            #    Patterns we reconstruct:
            #    ADJ '-' NOUN   -> "short-grain"
            #    NOUN '-' ADP   -> "skin-on" (allow 'on'/'in'/'off')
            for token in doc:
                if token.pos_ == "NOUN":
                    i = token.i
                    # look two tokens to the left for "X - Y"
                    if i - 2 >= 0:
                        left = doc[i - 2]
                        hyph = doc[i - 1]
                        # ADJ '-' NOUN  (e.g., short-grain rice)
                        if left.pos_ == "ADJ" and hyph.text == "-" and token.pos_ == "NOUN":
                            span = f"{left.text.lower()}-{token.nbor(-1).text.lower()}"
                            # but we used token itself, we need the noun after '-' which is at i-0 actually token; adjust:
                            # For ADJ '-' NOUN "short - grain rice", the NOUN after '-' is doc[i-0]? It's token,
                            # but we want the word at i-0? Safer: get the word just before current noun: doc[i-0] is current noun,
                            # while doc[i-1] is '-' ; doc[i-2] is ADJ; so the NOUN in the pair is doc[i], not nbor(-1).
                            # We'll recompute span below more robustly.
                    # recompute robust hyphen patterns with indices
            # re-run robust hyphen detection:
            for i, tok in enumerate(doc):
                # ADJ '-' NOUN before a head noun (e.g., "short - grain rice")
                if tok.pos_ == "ADJ" and i + 2 < len(doc) and doc[i+1].text == "-" and doc[i+2].pos_ == "NOUN":
                    span = f"{tok.text.lower()}-{doc[i+2].text.lower()}"
                    found.append((i, span))
                # NOUN '-' ADP (skin-on / bone-in / skin-off)
                if tok.pos_ == "NOUN" and i + 2 < len(doc) and doc[i+1].text == "-" and doc[i+2].text.lower() in hyphen_right_allow:
                    span = f"{tok.text.lower()}-{doc[i+2].text.lower()}"
                    found.append((i, span))

            # dedupe/order
            if found:
                found.sort(key=lambda x: x[0])
                dedup = []
                seen = set()
                for _, txt in found:
                    if txt not in seen and txt not in drop_adj:
                        seen.add(txt)
                        dedup.append(txt)
                descriptors_out.append(dedup or None)
            else:
                descriptors_out.append(None)

        self.descriptors = descriptors_out


    def extract_preparation(self):
        pass

    def answers():
        pass

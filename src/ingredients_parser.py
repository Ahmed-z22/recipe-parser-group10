import json
import re
from pathlib import Path

class IngredientsParser:
    def __init__(self, ingredients):
        self.ingredients = ingredients['ingredients']
        self.ingredients_names = None
        self.ingredients_quantities_and_amounts = None
        self.ingredients_measurement_units = None
        self.descriptor = None
        self.preparation = None

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
        pass

    def extract_preparation(self):
        pass

    def answers():
        pass

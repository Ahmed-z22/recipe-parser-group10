import json
import re
from pathlib import Path

class IngredientsParser:
    def __init__(self, ingredients):
        self.ingredients = ingredients['ingredients']
        self.names = None
        self.quantities = None
        self.units = None
        self.descriptor = None
        self.preparation = None

    def extract_names(self):
        pass

    def extract_quantities(self):
        pass

    def extract_units(self):
        pass

    def extract_descriptor(self):
        pass

    def extract_preparation(self):
        pass

    def answers():
        pass

    def convert_fractions(self):
        fractions_file = Path(__file__).resolve().parent / "helper_files" / "unicode_fractions.json"
        with fractions_file.open("r", encoding="utf-8") as f:
            unicode_fractions = json.load(f)

        fraction_chars = "".join(unicode_fractions.keys())
        pattern = re.compile(rf"(?:(\d+)\s*)?([{re.escape(fraction_chars)}])")

        updated = []
        for line in self.ingredients:
            new_line = pattern.sub(
                lambda m: (
                    f"{(float(m.group(1)) if m.group(1) else 0.0) + unicode_fractions[m.group(2)]:.4f}"
                ).rstrip("0").rstrip("."), 
                line
            )
            updated.append(new_line)

        self.ingredients = updated

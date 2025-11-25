from src.scraper import get_recipe_data
from src.ingredients_parser import IngredientsParser
from src.steps_parser import StepsParser
from src.methods_parser import MethodsParser
from src.tools_parser import ToolsParser
import re
from collections import Counter
import spacy
from urllib.parse import quote
from pathlib import Path
import json


class Chatbot:
    """Initialize Chatbot"""

    def __init__(self, test=False, backend=False):
        self.responses = [
            self._retrieval_query,
            self._navigation_query,
            self._parameter_query,
            self._procedure_query,
            self._clarification_query,
            self._quantity_query,
        ]

        self.path = Path(__file__).resolve().parent / "helper_files"
        usages_path = self.path / "usages.json"
        with open(usages_path, "r") as f:
            self.usages = json.load(f)

        procedures_path = self.path / "procedures.json"
        with open(procedures_path, "r") as f:
            self.procedures = json.load(f)

        self.step_words = [
            "first",
            "second",
            "third",
            "fourth",
            "fifth",
            "sixth",
            "seventh",
            "eigth",
            "ninth",
            "tenth",
            "eleventh",
            "twelfth",
            "thirteenth",
            "fourteenth",
            "fifteenth",
            "sixteenth",
            "seventeenth",
            "eighteenth",
            "nineteenth",
            "twentieth",
        ]
        self.number_words = [
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
            "twenty",
        ]

        self.query_types = [
            "retrieval_query",
            "navigation_query",
            "parameter_query",
            "procedure_query",
            "clarification_query",
            "quantity_query",
        ]

        self.query_patterns = [
            [  # retrieval_patterns
                r"\b(show|display|list|give|tell)\s+(me\s+)?(the\s+)?(recipe|ingredients?|directions?|steps?|instructions?)",
                r"\b(what|which)\s+(are\s+)?(the\s+)?(ingredients?|steps?)",
                r"\brecipe\b",
                r"\bingredients?\s+list\b",
            ],
            [  # navigation_patterns
                r"\b(go|move|jump|skip|take\s+me)\s+(to\s+)?(the\s+)?",
                r"\b(next|previous|prior|back|first|last)\s+(step|one)",
                r"\bgo\s+back\b",
                r"\bwhat\'?s?\s+next\b",
                r"\brepeat(\s+please|\s+that|\s+step)?\b",
                r"\bwhat\s+was\s+that(\s+again)?\b",
                r"\bagain\b",
                r"\bstart\s+over\b",
                r"\bwhat\s+is\s+(the\s+)?current\s+step\b",
                r"\bwhat\s+step\s+am\s+I\s+on\b",
                r"\bwhat\s+step\s+are\s+(we|you|they)\s+on\b",
                r"\bwhat\s+step\s+is\s+this\b",
                r"\bwhich\s+step\s+am\s+I\s+on\b",
                r"\bwhere\s+are\s+we\s+(in\s+the\s+recipe)?\b",
                r"\bwhat\s+step\s+are\s+we\s+at\b",
            ],
            [  # parameter_patterns
                r"\b(what|how\s+long|how\s+much)\s+time\b",
                r"\b(what|how\s+hot)\s+(temperature|temp)\b",
                r"\bhow\s+long\s+(do\s+I|to|should)",
                r"\bwhen\s+is\s+it\s+done\b",
                r"\bwhat\s+can\s+I\s+use\s+instead\b",
                r"\bsubstitute\b",
                r"\breplace\b",
                r"\bhow\s+(hot|warm|cold)\b",
            ],
            [  # procedure_patterns
                r"\bhow\s+do\s+(I|you)",
                r"\bhow\s+to\b",
                r"\bwhat\'?s\s+the\s+(way|method|process)\b",
                r"\bcan\s+you\s+(show|tell|explain)\s+me\s+how\b",
            ],
            [  # clarification_patterns
                r"\bwhat\s+is\s+(a\s+|an\s+)?",
                r"\bwhat\s+does\s+\w+\s+mean\b",
                r"\bwhat\'?s\s+(a\s+|an\s+)?",
                r"\bdefine\b",
                r"\bexplain\b",
                r"\bwhat\s+are\s+\w+\b(?!.*\bingredients?\b)",
            ],
            [  # quantity_patterns
                r"\b(how\s+much|how\s+many|what\s+amount)",
                r"\bhow\s+much\s+(\w+\s+)?(do\s+I\s+need|should\s+I|is\s+needed)\b",
                r"\bhow\s+many\s+(\w+\s+)?(do\s+I\s+need|should\s+I|is\s+needed)\b",
                r"\bhow\s+much\s+of\s+(that|this|it)\b",
            ],
        ]

        self.test = test

        if not backend:
            self._get_url()

        self.current_step = 0

    def process_url(self, url):
        """
        Parses metadata related to URL and stores in chatbot
        """

        if self.test:
            self.url = url
            self.title, self.raw_ingredients, self.raw_steps = get_recipe_data(url)
            self._process_metadata()
            return True

        try:
            self.url = url
            self.title, self.raw_ingredients, self.raw_steps = get_recipe_data(url)
            self._process_metadata()
            return True
        except:
            return False

    def _get_url(self):
        while True:
            if self.test:
                url = "https://www.allrecipes.com/recipe/166160/juicy-thanksgiving-turkey/"
            else:
                url = input("Please input the recipe URL: ")

            if self.process_url(url):
                break

    def _fix_step_grammar(self, step: str):
        """
        Corrects the grammar in each step
        """

        tokens = step.split()
        result = []

        if not tokens:
            return ""

        if tokens[0][0].isalpha():
            tokens[0] = tokens[0][0].upper() + tokens[0][1:]

        for i, token in enumerate(tokens):
            count = 0
            for c in token:
                if not c.isalnum():
                    count += 1

            if (token[0] == "f" or token[0] == "c") and count == len(token) - 1:
                token = token.upper()

            if len(result) > 0 and result[-1][-1] == "-":
                result[-1] += token
                continue

            if i > 0 and len(token) == 1 and not token.isalnum():
                result[-1] += token

            else:
                result.append(token)

        result = " ".join(result)

        if result[-1] == ".":
            return result

        if result[-1].isalnum() or result[-1] in ["]", ")", "}"]:
            return result + "."

        return result[:-1] + "."

    def _process_metadata(self):
        """
        Parses all metadata related to URL
        """

        ingredients = IngredientsParser(self.raw_ingredients)
        self.ingredients = ingredients.parse()
        if self.test:
            print("Ingredients parsed")

        methods = MethodsParser(self.raw_steps)
        self.methods = methods.parse()
        if self.test:
            print("Methods parsed")

        steps = StepsParser(self.raw_steps, self.ingredients)
        self.steps = steps.parse()

        for step in self.steps:
            step["description"] = self._fix_step_grammar(step["description"])

        if self.test:
            print("Steps parsed")

        tools = ToolsParser(self.raw_steps)
        self.tools = tools.parse()
        if self.test:
            print("Tools parsed")

        if self.test:
            self._debug_metadata()

        # supplement information between steps

    def _debug_metadata(self):
        print("Ingredients")
        for ingredient in self.ingredients:
            print(ingredient)
        print()

        print("Methods")
        for method in self.methods:
            print(method)
        print()

        print("Steps")
        for step in self.steps:
            print(step)
        print()

        print("Tools")
        for tool in self.tools:
            print(tool)
        print()

    """Answer Questions"""

    def converse(self):
        """
        Maintains continual loop of conversation while updating internal state
        """

        while True:
            query = input("Please input a question: ")
            print(self.respond(query))

    def respond(self, query):
        try:
            query = self._clean_query(query)
            if query == "what are the ingredients in the current step":
                ings = self.steps[self.current_step]["ingredients"]

                if len(ings) == 0:
                    return "There are no ingredients in the current step.\n"

                return f"The ingredients are: {', '.join(ings)}.\n"

            if query == "what are the tools in the current step":
                tools = self.steps[self.current_step]["tools"]

                if len(tools) == 0:
                    return "There are no tools in the current step.\n"

                return f"The tools are: {', '.join(tools)}.\n"

            if query == "what are the methods in the current step":
                methods = self.steps[self.current_step]["methods"]

                if len(methods) == 0:
                    return "There are no methods in the current step.\n"

                return f"The methods are: {', '.join(methods)}.\n"

            if "what kind of" in query:
                query = query.split()
                keyword = query[3]

                result = []
                for ing in self.ingredients:
                    if keyword in ing["ingredient_name"]:
                        if ing["ingredient_descriptors"] is not None:
                            result.append(" ".join(ing["ingredient_descriptors"]))

                        if ing["ingredient_preparation"] is not None:
                            result.append(" ".join(ing["ingredient_preparation"]))
                        break

                if len(result) == 0:
                    return "Unclear ingredient.\n"
                result.append(keyword)

                result = [
                    val
                    for i, val in enumerate(result)
                    if not (i > 0 and val == result[i - 1])
                ]
                result = " ".join(result)
                result = result[0].upper() + result[1:] + ".\n"

                return result

            question_type = self._identify_query(query)

            if question_type == -1:
                return "Unclear question type.\n"

            if self.test:
                print(self.query_types[question_type])

            return self.responses[question_type](query)
        except:
            return "Unclear question.\n"

    def _clean_query(self, query):
        """
        Cleans a question for further processing
        """

        query = query.lower().strip()
        query = query.rstrip("?")
        query = query.rstrip(".")
        query = " ".join(query.split())

        return query

    def _identify_query(self, query: str) -> int:
        """
        Identifies which of six questions the provided question is
        """

        if self.test and query[-1].isdigit():
            return int(query.split()[-1])

        if "define" in query:
            return 3

        # First check for regex matches
        for i in range(len(self.query_patterns)):
            if any(re.search(pattern, query) for pattern in self.query_patterns[i]):
                return i

        return -1

    """
    Retrieval Queries
    Requests to show a recipe or its components.
    Examples:
        "Show me the ingredients list."
        "Display the recipe."
    """

    def _get_title(self):
        return f' --- {self.title["title"]} --- \n'

    def _get_steps(self):
        result = " --- Steps --- \n"
        for i, step in enumerate(self.steps, start=1):
            result += f'{i}: {step["description"]}\n'
        result += "\n"

        return result

    def _get_ingredients(self):
        result = " --- Ingredients --- \n"
        for ingredient in self.raw_ingredients["ingredients"]:
            result += " - " + ingredient + "\n"
        result += "\n"

        return result

    def _get_step(self, idx):
        """
        Prints a specific atomic step based on 0-based index
        """

        if idx < 0 or idx == len(self.steps):
            return "No such step exists.\n"

        return self.steps[idx]["description"]

    def _retrieval_query(self, question: str):
        if "name" in question or "title" in question:
            return self._get_title()

        if "ingredient" in question:
            return self._get_ingredients()

        if "step" in question or "direction" in question:
            return self._get_steps()

        if "recipe" in question:
            return self._get_title() + self._get_ingredients() + self._get_steps()

        return "Unclear question."

    """
    Navigation Queries
    Moving between, repeating, or revisiting recipe steps.
    Examples:
        "Go back one step."
        "Go to the next step."
        "Repeat please."
        "Take me to the first step."
        "What’s next?"
        "What was that again?"
    """

    def _retrieve_step_index(self, question):
        if "last" in question:
            return len(self.steps) - 1

        for i in range(20):
            if self.step_words[i] in question or self.number_words[i] in question:
                return i

        numbers = re.findall(r"\d+", question)
        if len(numbers) == 0:
            return -1

        freq = Counter()
        for number in numbers:
            freq[int(number)] += 1

        return freq.most_common(1)[0][0]

    def _navigation_query(self, question: str):
        prev_keywords = ["back", "prior", "before", "prev"]
        cur_keywords = ["repeat", "again", "current"]
        next_keywords = ["next", "after"]

        next_step = -1
        if any([keyword in question for keyword in prev_keywords]):
            next_step = self.current_step - 1
        elif any([keyword in question for keyword in next_keywords]):
            next_step = self.current_step + 1
        elif any([keyword in question for keyword in cur_keywords]):
            next_step = self.current_step
        else:
            next_step = self._retrieve_step_index(question)

        if next_step < 0 or next_step >= len(self.steps):
            return "No such step exists."

        self.current_step = next_step
        return self._get_step(self.current_step)

    """
    Parameter Queries
    Asking about quantities, times, temperatures, or substitutes within the current step.
    Examples:
        "How much salt do I need?"
        "What temperature should the oven be?"
        "How long do I bake it?"
        "When is it done?"
        "What can I use instead of butter?"
    """

    def _parameter_query(self, question):
        time_keywords = ["long", "time", "when", "done", "finished", "complete"]
        substitute_keywords = ["instead", "use", "replace", "what"]
        temperature_keywords = [
            "temperature",
            "what",
            "heat",
            "cold",
            "warm",
            "hot",
            "lukewarm",
        ]

        counts = [
            sum([question.count(keyword) for keyword in time_keywords]),
            sum([question.count(keyword) for keyword in substitute_keywords]),
            sum([question.count(keyword) for keyword in temperature_keywords]),
        ]

        step = self.steps[self.current_step]

        idx = counts.index(max(counts))

        if counts[idx] == 0:
            return "Can you please elaborate on your query?\n"

        elif idx == 0:  # time
            if step["time"] == None:
                return "No time available for this step.\n"

            return f'{step["time"]["duration"]}.\n'

        # elif idx == 1:  # substitute
        #     return "Substitutes currently unavailble.\n"

        elif idx == 2:  # temperature
            if step["temperature"] == None:
                return "No temperature available for this step.\n"

            return f'{step["temperature"]["value"]} {step["temperature"]["unit"]}.\n'

    """
    Clarification Queries
    Asking for definitions or explanations of terms or tools.
    Examples:
        "What is a whisk?"
    """

    def _extract_keyword(self, question):
        """
        Extracts keywords for clarification
        """

        cleaned = question.rstrip("?")
        cleaned = question.rstrip(".")

        patterns = [
            r"^what\s+is\s+(a\s+|an\s+)?",  # "what is a/an"
            r"^what\s+does\s+",  # "what does"
            r"^what\s+are\s+",  # "what are"
            r"^how\s+do\s+you\s+",  # "how do you"
            r"^what\'s\s+(a\s+|an\s+)?",  # "what's a/an"
        ]

        keyword = cleaned

        for pattern in patterns:
            keyword = re.sub(pattern, "", keyword)

        trailing_patterns = [
            r"\s+mean$",
            r"\s+used\s+for$",
            r"\s+do$",
        ]

        for pattern in trailing_patterns:
            keyword = re.sub(pattern, "", keyword)

        keyword = " ".join(keyword.split())

        return keyword

    def _get_youtube_link(self, query):
        encoded_query = quote(query)
        return f"https://www.youtube.com/results?search_query={encoded_query}"

    def _clarification_query(self, query):
        keyword = self._extract_keyword(query)

        tokens = keyword.split()
        counter = Counter()

        usage = ""
        definition = ""
        for tool in self.usages:
            tool_tokens = tool.split()
            for token in tokens:
                for tool_tok in tool_tokens:
                    if token == tool_tok:
                        counter[tool] += 1

        result = ""
        if len(counter) > 0:
            tool = counter.most_common(1)[0][0]
            usage = self.usages[tool]["usage"]
            definition = self.usages[tool]["description"]
            result = f"{tool[0].upper() + tool[1:]} refers to {definition[0].lower() + definition[1:]}. {usage}\n"

            result += f"Here is a YouTube search which may help further clarify your query: {self._get_youtube_link(query)}"

            return result

        return "Please clarify your query.\n"

    """
    Procedure Queries
    Asking how to perform an action or technique.
    Specific: "How do I knead the dough?"
    Vague (step-dependent): "How do I do that?" — referring to the current step’s action.
    """

    def _procedure_query(self, query):
        tokens = query.split()
        keyword = tokens[-1]

        tokens = keyword.split()
        counter = Counter()

        for procedure in self.procedures:
            proc_tokens = procedure.split()
            for token in tokens:
                for proc_tok in proc_tokens:
                    if token == proc_tok:
                        counter[procedure] += 1

        result = ""
        if len(counter) > 0:
            mx = counter.most_common(1)[0][0]
            result += f"{mx[0].upper() + mx[1:]} means {self.procedures[mx][0].lower() + self.procedures[mx][1:]}\n"

        result += f"Here is a YouTube search which may help further clarify your query: {self._get_youtube_link(query)}\n"

        return result

    """
    Quantity Queries
    Asking about ingredient amounts.
    Specific: "How much flour do I need?"
    Vague (step-dependent): "How much of that do I need?" — referring to an ingredient mentioned in the current step.
    """

    def _get_ingredient_quantity(self, query):
        quantity = -1
        unit = ""
        for ingredient in self.ingredients:
            if query in ingredient["ingredient_name"]:
                quantity = ingredient["ingredient_quantity"]
                unit = ingredient["measurement_unit"]
                break

        if quantity == "":
            return None, None

        if unit == None:
            return quantity, False

        return f"{quantity} {unit}", True

    def _quantity_query(self, question):
        step = self.steps[self.current_step]
        tokens = self._extract_keyword(question).split()
        counter = Counter()
        for idx, ing in enumerate(self.ingredients):
            for tok in tokens:
                if tok in ing["ingredient_name"]:
                    counter[idx] += 1

        if len(counter) == 0:
            ingredient = step["ingredients"]

            if ingredient == None:
                return "No ingredients mentioned\n"

            ingredient = ingredient[0]
        else:
            idx = counter.most_common(1)[0][0]
            ingredient = self.ingredients[idx]["ingredient_name"]

        quantity, unit = self._get_ingredient_quantity(ingredient)

        if quantity == "":
            return f"No quantity is available for the ingredient {ingredient}\n"

        if unit:
            return f"{quantity} of {ingredient}.\n"
        else:
            return f"{quantity} {ingredient}.\n"


if __name__ == "__main__":
    chatbot = Chatbot()
    chatbot.converse()

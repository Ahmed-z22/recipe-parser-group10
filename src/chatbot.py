from scraper import get_recipe_data
from ingredients_parser import IngredientsParser
from steps_parser import StepsParser
from methods_parser import MethodsParser
from tools_parser import ToolsParser
import re
from collections import Counter

class Chatbot:
    """
    Answers user's questions about recipes in conversational manner
    """
    
    def __init__(self, test=False):
        self.responses = [
            self._retrieval_query,
            self._navigation_query,
            self._parameter_query,
            self._clarification_query,
            self._procedure_query,
            self._quantity_query,
        ]

        self.test = test

        self._get_url()
        self._parse_metadata()

        self.current_step = 0

    def _get_url(self):
        while True:
            if self.test:
                url = "https://www.allrecipes.com/amish-beef-and-noodles-recipe-8712456"
            else:
                url = input('Please input the recipe URL: ')

            try:
                self.url = url
                self.title, self.raw_ingredients, self.raw_steps = get_recipe_data(url)
                break
            except:
                pass

    def _parse_metadata(self):
        ingredients = IngredientsParser(self.raw_ingredients)
        self.ingredients = ingredients.parse()

        methods = MethodsParser(self.raw_steps)
        self.methods = methods.parse()

        steps = StepsParser(self.raw_steps, self.ingredients)
        self.steps = steps.parse()

        tools = ToolsParser(self.raw_steps)
        self.tools = tools.parse()

        if self.test:
            self._print_metadata()

    def _print_metadata(self):
        print('Ingredients')
        for ingredient in self.ingredients:
            print(ingredient)
        print()

        print('Methods')
        for method in self.methods:
            print(method)
        print()

        print('Steps')
        for step in self.steps:
            print(step)
        print()

        print('Tools')
        for tool in self.tools:
            print(tool)
        print()

    def converse(self):
        """
        Maintains continual loop of conversation while updating internal state
        """

        while True:
            question = input('Please input a question: ')
            question = self._clean_question(question)
            question_type = self._identify_query(question)

            if question_type == -1:
                print('Unclear question type.')
                print()
                continue

            self.responses[question_type](question)
            print()

    def _clean_question(self, question):
        """
        Cleans a question for further processing
        """

        question = question.lower().strip()
        question = question.rstrip('?')
        question = question.rstrip('.')
        question = ' ' .join(question.split())

        return question

    def _identify_query(self, question: str) -> int:
        """
        Identifies which of six questions the provided question is
        """

        patterns = [
            [ # retrieval_patterns 
                r'\b(show|display|list|give|tell)\s+(me\s+)?(the\s+)?(recipe|ingredients?|directions?|steps?|instructions?)',
                r'\b(what|which)\s+(are\s+)?(the\s+)?(ingredients?|steps?)',
                r'\brecipe\b',
                r'\bingredients?\s+list\b',
            ],
            [ # navigation_patterns 
                r'\b(go|move|jump|skip|take\s+me)\s+(to\s+)?(the\s+)?(next|previous|back|forward|first|last)',
                r'\b(next|previous|prior|back|first|last)\s+(step|one)',
                r'\bgo\s+back\b',
                r'\bwhat\'?s?\s+next\b',
                r'\brepeat(\s+please|\s+that|\s+step)?\b',
                r'\bwhat\s+was\s+that(\s+again)?\b',
                r'\bagain\b',
                r'\bstart\s+over\b',
            ],
            [ # parameter_patterns 
                r'\b(how\s+much|how\s+many|what\s+amount)',
                r'\b(what|how\s+long|how\s+much)\s+time\b',
                r'\b(what|how\s+hot)\s+(temperature|temp)\b',
                r'\bhow\s+long\s+(do\s+I|to|should)',
                r'\bwhen\s+is\s+it\s+done\b',
                r'\bwhat\s+can\s+I\s+use\s+instead\b',
                r'\bsubstitute\b',
                r'\breplace\b',
                r'\bhow\s+(hot|warm|cold)\b',
            ],
            [ # clarification_patterns 
                r'\bwhat\s+is\s+(a\s+|an\s+)?',
                r'\bwhat\s+does\s+\w+\s+mean\b',
                r'\bwhat\'?s\s+(a\s+|an\s+)?',
                r'\bdefine\b',
                r'\bexplain\b',
                r'\bwhat\s+are\s+\w+\b(?!.*\bingredients?\b)',
            ],
            [ # procedure_patterns 
                r'\bhow\s+do\s+(I|you)',
                r'\bhow\s+to\b',
                r'\bwhat\'?s\s+the\s+(way|method|process)\b',
                r'\bcan\s+you\s+(show|tell|explain)\s+me\s+how\b',
            ],
            [ # quantity_patterns 
                r'\bhow\s+much\s+(\w+\s+)?(do\s+I\s+need|should\s+I|is\s+needed)\b',
                r'\bhow\s+many\s+(\w+\s+)?(do\s+I\s+need|should\s+I|is\s+needed)\b',
                r'\bhow\s+much\s+of\s+(that|this|it)\b',
            ],
        ]

        for i in range(len(patterns)):
            if any(re.search(pattern, question) for pattern in patterns[i]):
                return i

        return -1

    def _retrieval_query(self, question: str):
        """
        Requests to show a recipe or its components.
        Examples:
            "Show me the ingredients list."
            "Display the recipe."
        """
        
        if 'recipe' in question:
            self._print_title()
            self._print_ingredients()
            self._print_steps()
            return

        if 'name' in question or 'title' in question:
            self._print_title()

        if 'ingredient' in question:
            self._print_ingredients()

        if 'step' in question or 'direction' in question:
            self._print_steps()

    def _print_title(self):
        print(f' --- {self.title['title']} --- ')
        print()

    def _print_steps(self):
        print(' --- Steps --- ')
        for step in self.steps:
            print(f'{step['step_number']}: {step['description']}')
        print()

    def _print_ingredients(self):
        print(' --- Ingredients --- ')
        for ingredient in self.raw_ingredients['ingredients']:
            print(' -', ingredient)
        print()

    def _navigation_query(self, question: str):
        """
        Moving between, repeating, or revisiting recipe steps.
        Examples:
            "Go back one step."
            "Go to the next step."
            "Repeat please."
            "Take me to the first step."
            "What’s next?"
            "What was that again?"
        """

        prev_keywords = ['back', 'prior', 'before', 'prev']
        cur_keywords = ['repeat', 'again', 'current']
        next_keywords = ['next', 'after']

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
            print('No such step exists.')
            return

        self.current_step = next_step
        self._print_step(self.current_step)

    def _print_step(self, idx):
        """
        Prints a specific atomic step based on 0-based index
        """

        if idx < 0 or idx == len(self.steps):
            print('No such step exists.')
            return

        print(self.steps[idx]['description'])

    def _retrieve_step_index(self, question):
        if 'last' in question:
            return len(self.steps) - 1

        step = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eigth', 'ninth', 'tenth', 'eleventh', 'twelfth', 'thirteenth', 'fourteenth', 'fifteenth', 'sixteenth', 'seventeenth', 'eighteenth', 'nineteenth', 'twentieth' ]
        words = [ 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty']

        for i in range(20):
            if step[i] in question or words[i] in question:
                return i

        numbers = re.findall(r'\d+', question)
        if len(numbers) == 0:
            return -1

        freq = Counter()
        for number in numbers:
            freq[int(number)] += 1
        
        return freq.most_common(1)[0][0]

    def _parameter_query(self, question):
        """
        Asking about quantities, times, temperatures, or substitutes within the current step.
        Examples:
            "How much salt do I need?"
            "What temperature should the oven be?"
            "How long do I bake it?"
            "When is it done?"
            "What can I use instead of butter?"
        """

        quantity_keywords = ['much', 'how', 'quant']
        time_keywords = ['long', 'time', 'when']
        substitute_keywords = ['instead', 'use', 'replace', 'what']
        temperature_keywords = ['temperature', 'what', 'heat', 'cold']

        counts = [
            sum([question.count(keyword) for keyword in quantity_keywords]),
            sum([question.count(keyword) for keyword in time_keywords]),
            sum([question.count(keyword) for keyword in substitute_keywords]),
            sum([question.count(keyword) for keyword in temperature_keywords]),
        ]

        step = self.steps[self.current_step]

        idx = counts.index(max(counts))

        if counts[idx] == 0:
            print('Unclear query.')
            return

        if idx == 0: # quantity
            ingredient = step['ingredients']

            if ingredient == None:
                print('No ingredients mentioned')
                return

            ingredient = ingredient[0]
            quantity = self._get_ingredient_quantity(ingredient)

            if quantity == '':
                print(f'No quantity is available for the ingredient {ingredient}')
                return

            print(f'{quantity} of {ingredient}.')

        elif idx == 1: # time
            if step['time'] == None:
                print('No time available for this step.')
                return

            print(f'{step['time']['duration']}.')

        elif idx == 2: # substitute
            print('Substitutes currently unavailble.')

        elif idx == 3: # temperature
            if step['temperature'] == None:
                print('No temperature available for this step.')
                return

            print(f'{step['temperature']['value']} {step['temperature']['unit']}.')

    def _get_ingredient_quantity(self, query):
        quantity = -1
        unit = ''
        for ingredient in self.ingredients:
            if query in ingredient['ingredient_name']:
                quantity = ingredient['ingredient_quantity']
                unit = ingredient['measurement_unit']
                break

        if quantity == '':
            return None

        return f'{quantity} {unit}'


    def _clarification_query(self, question):
        """
        Asking for definitions or explanations of terms or tools.
        Examples:
            "What is a whisk?"
        """

        keyword = self._extract_keyword(question)

        for tool in self.tools:
            if keyword in tool['direction']:
                print('Usage not yet supported.')
                return

        for method in self.methods:
            if keyword in method['direction']:
                print('Clarification not yet supported')
                return
    
    def _extract_keyword(self, question):
        cleaned = question.rstrip('?')
        cleaned = question.rstrip('.')

        patterns = [
            r'^what\s+is\s+(a\s+|an\s+)?', # "what is a/an"
            r'^what\s+does\s+', # "what does"
            r'^what\s+are\s+', # "what are"
            r'^who\s+is\s+', # "who is"
            r'^how\s+do\s+you\s+', # "how do you"
            r'^what\'s\s+(a\s+|an\s+)?', # "what's a/an"
        ]
        
        keyword = cleaned

        for pattern in patterns:
            keyword = re.sub(pattern, '', keyword)

        trailing_patterns = [
            r'\s+mean$',
            r'\s+used\s+for$',
            r'\s+do$',
        ]

        for pattern in trailing_patterns:
            keyword = re.sub(pattern, '', keyword)

        keyword = ' '.join(keyword.split())

        return keyword

    def _procedure_query(self, question):
        """
        Asking how to perform an action or technique.
        Specific: "How do I knead the dough?"
        Vague (step-dependent): "How do I do that?" — referring to the current step’s action.
        """

        step = self.steps[self.current_step]
        methods = step['methods']

        if methods == None:
            print('No methods corresponding to this step.')
            return

        print('Procedure not yet supported.')

    def _quantity_query(self, question):
        """
        Asking about ingredient amounts.
        Specific: "How much flour do I need?"
        Vague (step-dependent): "How much of that do I need?" — referring to an ingredient mentioned in the current step.
        """

        step = self.steps[self.current_step]
        ingredient = step['ingredients']

        if ingredient == None:
            print('No ingredients mentioned')
            return

        ingredient = ingredient[0]
        quantity = self._get_ingredient_quantity(ingredient)

        if quantity == '':
            print(f'No quantity is available for the ingredient {ingredient}')
            return

        print(f'{quantity} of {ingredient}.')

if __name__ == '__main__':
    chatbot = Chatbot()
    chatbot.converse()


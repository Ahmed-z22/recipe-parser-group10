import json
import re
import spacy
from pathlib import Path
from typing import List, Dict, Any, Optional
from tools_parser import ToolsParser
from methods_parser import MethodsParser


class StepsParser:
    """Parses recipe directions into atomic steps with annotations."""
    
    def __init__(self, directions: Dict[str, List[str]], parsed_ingredients: List[Dict[str, Any]]):
        """Initialize parser with directions and parsed ingredients.
        
        Args:
            directions: Dict with 'directions' key containing list of direction strings
            parsed_ingredients: List of ingredient dicts from IngredientsParser.parse()
        """
        self.directions = directions['directions']
        self.parsed_ingredients = parsed_ingredients
        self.nlp = spacy.load("en_core_web_sm")
        
        # reuse existing parsers so we don't duplicate code
        self.tools_parser = ToolsParser(directions)
        self.methods_parser = MethodsParser(directions)
        
        # load method keywords for classifying step types
        self.path = Path(__file__).resolve().parent / "helper_files"
        method_keywords_path = self.path / "method_keywords.json"
        with open(method_keywords_path, 'r') as f:
            methods_data = json.load(f)
        self.method_keywords = methods_data.get('method_keywords', [])
        
        # lowercase ingredient names for matching, keep original for output
        self.ingredient_names = [ing['ingredient_name'].lower() for ing in parsed_ingredients]
        self.ingredient_name_map = {
            ing['ingredient_name'].lower(): ing['ingredient_name'] 
            for ing in parsed_ingredients
        }
        
        # track context like oven temp so later steps can use it
        self.context = {
            'oven_temperature': None
        }
    
    def split_directions_into_atomic_steps(self) -> List[str]:
        """Split directions into atomic steps.
        
        Returns:
            List of atomic step strings
        """
        all_steps = []
        
        for direction in self.directions:
            # split by sentences using spacy
            doc = self.nlp(direction)
            sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
            
            for sent in sentences:
                # check if sentence has multiple actions (like "mix and stir")
                sent_doc = self.nlp(sent)
                split_points = []
                
                # look for "and" or "then" connecting verbs
                for i, tok in enumerate(sent_doc):
                    if tok.text.lower() in ['and', 'then'] and i > 0 and i < len(sent_doc) - 1:
                        left_has_verb = any(t.pos_ == 'VERB' for t in sent_doc[:i])
                        right_has_verb = any(t.pos_ == 'VERB' for t in sent_doc[i+1:])
                        
                        if left_has_verb and right_has_verb:
                            split_points.append(i)
                
                # split at the points we found
                if split_points:
                    parts = []
                    start = 0
                    for split_idx in split_points:
                        part_text = ' '.join([t.text for t in sent_doc[start:split_idx]]).strip()
                        if part_text:
                            parts.append(part_text)
                        start = split_idx + 1
                    
                    # get the last part too
                    if start < len(sent_doc):
                        part_text = ' '.join([t.text for t in sent_doc[start:]]).strip()
                        if part_text:
                            parts.append(part_text)
                    
                    if len(parts) > 1:
                        all_steps.extend(parts)
                    else:
                        all_steps.append(sent)
                else:
                    all_steps.append(sent)
        
        return all_steps
    
    def extract_ingredients_from_step(self, step: str) -> List[str]:
        """Find ingredients mentioned in the step.
        
        Args:
            step: Step text to analyze
            
        Returns:
            List of ingredient names
        """
        step_lower = step.lower()
        mentioned_ingredients = []
        
        # match ingredients case-insensitively
        for ingredient_name_lower in self.ingredient_names:
            original_name = self.ingredient_name_map[ingredient_name_lower]
            words = ingredient_name_lower.split()
            
            if len(words) == 1:
                # single word - use word boundary so "salt" doesn't match "salted"
                pattern = r'\b' + re.escape(ingredient_name_lower) + r'\b'
                if re.search(pattern, step_lower):
                    mentioned_ingredients.append(original_name)
            else:
                # try exact match first
                if ingredient_name_lower in step_lower:
                    mentioned_ingredients.append(original_name)
                else:
                    # fallback: match by main noun (last word usually)
                    main_word = words[-1]
                    if len(main_word) > 3:  # skip short words
                        main_pattern = r'\b' + re.escape(main_word) + r'\b'
                        if re.search(main_pattern, step_lower):
                            mentioned_ingredients.append(original_name)
        
        # remove duplicates, keep order
        seen = set()
        unique_ingredients = []
        for ing in mentioned_ingredients:
            if ing.lower() not in seen:
                seen.add(ing.lower())
                unique_ingredients.append(ing)
        
        return unique_ingredients
    
    def extract_tools(self, step: str) -> List[str]:
        """Extract tools mentioned in the step.
        
        Args:
            step: Step text to analyze
            
        Returns:
            List of tool names
        """
        return self.tools_parser.extract_tools(step)
    
    def extract_methods(self, step: str) -> List[str]:
        """Extract cooking methods from the step.
        
        Args:
            step: Step text to analyze
            
        Returns:
            List of cooking methods
        """
        return self.methods_parser.extract_methods(step)
    
    def extract_time(self, step: str) -> Optional[Dict[str, str]]:
        """Extract time/duration from step text.
        
        Args:
            step: Step text to analyze
            
        Returns:
            Dict with 'duration' key, or None if no time found
        """
        step_lower = step.lower()
        
        # TODO: handle more time formats (seconds, days, "about X minutes")
        # explicit durations like "30 minutes", "2 hours"
        time_patterns = [
            (r'(\d+)\s*(?:minutes?|mins?)', 'minutes'),
            (r'(\d+)\s*(?:hours?|hrs?)', 'hours'),
        ]
        
        for pattern, unit in time_patterns:
            match = re.search(pattern, step_lower)
            if match:
                num = match.group(1)
                return {"duration": f"{num} {unit}"}
        
        # time ranges like "20-30 minutes"
        range_pattern = r'(\d+)\s*[-–]\s*(\d+)\s*(minutes?|hours?)'
        range_match = re.search(range_pattern, step_lower)
        if range_match:
            start, end, unit = range_match.groups()
            return {"duration": f"{start}-{end} {unit}"}
        
        # "until" phrases like "until golden brown"
        until_pattern = r'until\s+([^,\.;]+?)(?:[,\.;]|$)'
        until_match = re.search(until_pattern, step_lower)
        if until_match:
            condition = until_match.group(1).strip()
            return {"duration": f"until {condition}"}
        
        # "for" phrases like "for 30 minutes"
        for_pattern = r'for\s+(\d+)\s*(minutes?|hours?|mins?|hrs?)'
        for_match = re.search(for_pattern, step_lower)
        if for_match:
            num, unit = for_match.groups()
            return {"duration": f"{num} {unit}"}
        
        return None
    
    def extract_temperature(self, step: str) -> Optional[Dict[str, str]]:
        """Extract temperature from step text.
        
        Args:
            step: Step text to analyze
            
        Returns:
            Dict with 'value' and 'unit' keys, or None if no temperature found
        """
        step_lower = step.lower()
        
        # TODO: add celsius support
        # oven temps 
        oven_keywords = ['preheat', 'oven', 'bake', 'roast', 'broil']
        is_oven_step = any(keyword in step_lower for keyword in oven_keywords)
        
        if is_oven_step:
            # look for temperature numbers
            temp_patterns = [
                r'(\d+)\s*°?\s*[Ff]',
                r'(\d+)\s+degrees?',
                r'(?:preheat|heat)\s+(?:oven\s+)?to\s+(\d+)',
            ]
            
            for pattern in temp_patterns:
                match = re.search(pattern, step_lower)
                if match:
                    temp = match.group(1)
                    self.context['oven_temperature'] = f"{temp}°F"
                    return {"value": temp, "unit": "°F"}
        
        # ingredient temps like "chicken to 165°F" - assume fahrenheit
        ingredient_temp_pattern = r'(\w+)\s+to\s+(\d+)'
        ingredient_match = re.search(ingredient_temp_pattern, step_lower)
        if ingredient_match:
            ingredient = ingredient_match.group(1)
            temp = ingredient_match.group(2)
            return {"value": temp, "unit": "°F", "ingredient": ingredient}
        
        # heat levels like "medium heat"
        heat_level_pattern = r'(low|medium|high)\s+heat'
        heat_match = re.search(heat_level_pattern, step_lower)
        if heat_match:
            level = heat_match.group(1)
            return {"value": level, "unit": "heat"}
        
        return None
    
    def classify_step_type(self, step: str) -> str:
        """Classify step as actionable, warning, advice, or observation.
        
        Args:
            step: Step text to classify
            
        Returns:
            Step type string ("actionable", "warning", "advice", or "observation")
        """
        step_lower = step.lower()
        
        # check warnings first
        warning_keywords = ['careful', "don't", 'avoid', 'warning', 'do not', 'never']
        if any(keyword in step_lower for keyword in warning_keywords):
            return "warning"
        
        # advice
        advice_keywords = ['optional', 'alternatively', 'tip', 'you can', 'or', 'may', 'might']
        if any(keyword in step_lower for keyword in advice_keywords):
            return "advice"
        
        # observations - usually describe state changes
        observation_keywords = ['will', 'should be', 'may become', 'it should', 'they should']
        if any(keyword in step_lower for keyword in observation_keywords):
            if step_lower.startswith(('the ', 'it ', 'they ')):
                return "observation"
        
        # default to actionable
        return "actionable"
    
    def parse(self) -> List[Dict[str, Any]]:
        """Parse directions into annotated atomic steps.
        
        Returns:
            List of step dictionaries with annotations
        """
        atomic_steps = self.split_directions_into_atomic_steps()
        
        parsed_steps = []
        
        # TODO: propagate context (e.g., carry oven temp to later baking steps)
        for i, step_text in enumerate(atomic_steps, start=1):
            step_ingredients = self.extract_ingredients_from_step(step_text)
            step_tools = self.extract_tools(step_text)
            step_methods = self.extract_methods(step_text)
            time_info = self.extract_time(step_text)
            temp_info = self.extract_temperature(step_text)
            step_type = self.classify_step_type(step_text)
            
            step_dict = {
                "step_number": i,
                "description": step_text,
                "ingredients": step_ingredients,
                "tools": step_tools,
                "methods": step_methods,
                "time": time_info,
                "temperature": temp_info,
                "type": step_type
            }
            
            parsed_steps.append(step_dict)
        
        return parsed_steps


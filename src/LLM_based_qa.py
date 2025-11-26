from dotenv import load_dotenv
from google import genai
from google.genai import types
import os
from pathlib import Path
from src.scraper import get_recipe_data

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RESET = "\033[0m"
BOLD = "\033[1m"

class LLMBasedQA:
    def __init__(self, url, model_name="gemini-2.5-flash-lite"):

        self.path = Path(__file__).resolve().parent.parent
        load_dotenv(self.path / "apikey.env")
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Please set it in your .env file."
            )

        with open(self.path / "src" / "prompts" / "prompt_part2.txt", "r") as f:
            self.system_prompt = f.read()

        self.client = genai.Client()
        self.chat = self.client.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=0.2,
                top_p=0.8,
                top_k=40,
            ),
        )

        self.title, self.ingredients, self.directions = get_recipe_data(url)

    def _question_formatting(self, question: str, title: str, ingredients: list, steps: list) -> (str, str):
        return (
            (
                "=== RECIPE DATA START ===\n"
                f"Title:\n{title}\n\n"
                "Ingredients:\n" + "\n".join(ingredients) + "\n\n"
                "Steps:\n" + "\n".join(steps) + "\n"
                "=== RECIPE DATA END ===\n\n"
                "User Question:\n"
                f"{question}\n\n"
                "Answer:"
            ),
            question,
        )
    
    def answer(self, question: str) -> (str, str):
        formatted_question, user_question = self._question_formatting(
            question, self.title["title"], self.ingredients["ingredients"], self.directions["directions"]
        )
        self.chat.send_message(formatted_question)
        return user_question, self.chat.get_history()[-1].parts[0].text

if __name__ == "__main__":
    print(BOLD + CYAN + "\n=== Recipe Explainer Chatbot ===\n" + RESET)

    input_url = input(YELLOW + "Enter the recipe URL: " + RESET)

    llm_qa = LLMBasedQA(input_url)

    print(CYAN + "\n------------------------------------------------------------" + RESET)
    print(BOLD + "You can now ask questions about the recipe." + RESET)
    print("(Type 'exit' or 'quit' to stop)")
    print(CYAN + "------------------------------------------------------------\n" + RESET)

    while True:
        user_question = input(GREEN + "You: " + RESET)

        if user_question.lower() in ("exit", "quit"):
            print(CYAN + "\nGoodbye!\n" + RESET)
            break

        question, answer = llm_qa.answer(user_question)

        print(BOLD + MAGENTA + "Assistant:" + RESET)
        print(f"{answer}\n")
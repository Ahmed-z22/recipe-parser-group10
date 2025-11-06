from src.scraper import get_recipe_data

def parse_question(question):
    """
    Recipe retrieval and display (see example above, including "Show me the ingredients list")

    Navigation utterances ("Go back one step", "Go to the next step", "Repeat please", "Take me to the 1st step", "What's next?", "What was that again?")

    Asking about the parameters of the current step ("How much of <ingredient> do I need?", "What temperature?", "How long do I <specific technique>?", "When is it done?", "What can I use instead of <ingredient or tool>")

    Simple "what is" questions ("What is a <tool being mentioned>?")

    Specific "how much" questions ("How much <ingredient> do I need?").

    Vague "how much" questions ("How much of that do I need?").

    Specific "how to" questions ("How do I <specific technique>?").

    Vague "how to" questions ("How do I do that?" – use conversation history to infer what “that” refers to)
    """

    pass

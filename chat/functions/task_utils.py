import re

from chat.utils import get_possible_topics

# Mapping of keywords to tasks
TASK_KEYWORDS = {
    "inventory": [
        "update inventory", "inventory", "manage inventory", "check stock", 
        "i want to update my inventory", "add to inventory", "remove from inventory",
        "list inventory", "inventory report", "stock report", "kailangan iupdate ang inventory",
        "dagdag sa inventory", "alisin sa inventory", "tingnan ang inventory", 
        "update ang stock", "update ang inventory", "inventory status", "check inventory",
        "magupdate ng inventory", "gusto kong magupdate ng inventory", 
        "pwede bang makita ang inventory", "inventory ng tindahan", 
        "stock ng mga items", "iupdate ang mga produkto", 
        "update ng stock sa tagalog", "tingnan ang stock", 
        "iupdate ko ang inventory", "how to update inventory", 
        "gusto ko imanage ang inventory", "inventory listahan",
        "tingnan ang inventory ko", "stocks update", "manage ng inventory"
    ],
    "sales": [
        "update POS", "POS", "sales", "point of sale", "manage sales", 
        "update point of sale", "edit sales", "check sales", 
        "sales management", "handle POS", "manage POS", 
        "tingnan ang benta", "tingnan ang POS", "iupdate ang POS", 
        "imanage ang POS", "iupdate ang point of sale", "ayosin ang benta", 
        "magmanage ng POS", "iedit ang benta", "ayusin ang POS",
        "check POS", "edit POS", "update ang POS", 
        "manage ng point of sale", "POS management", "POS update", 
        "benta update", "sales update", "POS tingnan", 
        "POS ayusin", "POS handle", "POS settings"
    ],
    "analyze": [
        "sales report", "sales status", "check sales history", 
        "generate report", "analyze sales", "how much did I sell",
        "review sales data", "sales insights", "performance report",
        "weekly sales", "daily sales", "how are my sales doing",
        "POS analytics", "POS reports", "sales trends",
        "POS summary", "profit summary", "benta summary",
        "kita report", "analyze kita", "kita ko today",
        "analyze ng benta", "kita status", "sales overview"
    ],
    "other": [
        "help", "cancel", "change topic", "exit", "info", "random", "tutorial",
        "privacy policy", "support", "system guide", "how does this work"
    ]
}

def identify_task(message, facebook_page_instance):
    """
    Identify the task based on the user's message, considering feature toggles.
    :param message: The text message from the user.
    :param facebook_page_instance: The FacebookPage instance to check enabled features.
    :return: A task string corresponding to the identified topic or None if no match.
    """
    # Normalize the message: trim spaces/newlines, convert to lowercase, and remove special characters
    normalized_message = re.sub(r'[^\w\s]', '', message.strip().lower())

    # Get available topics based on feature toggles
    enabled_topics = set(get_possible_topics(facebook_page_instance))

    # Create a filtered keyword mapping based on enabled features
    filtered_task_keywords = {
        task: keywords for task, keywords in TASK_KEYWORDS.items() if task in enabled_topics
    }

    for task, keywords in filtered_task_keywords.items():
        # Check if the normalized message exactly matches any keyword
        if normalized_message in [keyword.lower() for keyword in keywords]:
            print("MANUAL CHANGE", task)
            return task

    return None

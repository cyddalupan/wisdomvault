import re

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
    "pos": [
        "update POS", "POS", "point of sale", "manage sales", 
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
    "customer": ["customer support", "help customer", "customer query"],
}

def identify_task(message):
    """
    Identify the task based on the user's message.
    :param message: The text message from the user.
    :return: A task string corresponding to the identified topic or None if no match.
    """
    # Normalize the message: trim spaces/newlines, convert to lowercase, and remove special characters
    normalized_message = re.sub(r'[^\w\s]', '', message.strip().lower())

    for task, keywords in TASK_KEYWORDS.items():
        # Normalize keywords to lowercase and check against the normalized message
        if any(keyword.lower() in normalized_message for keyword in keywords):
            return task

    return None


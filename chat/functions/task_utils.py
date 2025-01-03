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
    "other": [
        # Cancellation Keywords
        "never mind", "cancel conversation", "stop conversation", 
        "back", "go back", "balik", "end chat", "tapusin", 
        "exit", "finished", "leave", "stop it", "suko na", 
        "enough", "hinto na", "huwag na", "huwag mo nang ituloy", 
        "exit chat", "tapos na", "stop na", "sapat na",

        # General Help or Assistance
        "help", "kailangan ko ng tulong", "assist", "assistance", 
        "support", "query", "tanong", "general question", "tulong", 
        "help me", "can you assist", "paano ito", "help naman", 
        "ano gagawin", "assist me", "may tanong ako", "can you help", 
        "can you explain", "kailangan ng paliwanag", "pa-assist", 
        "ano na", "ano meron", "help mo ako", 

        # General Information Requests
        "about", "more info", "info", "information", 
        "tell me", "explain", "details", "ano ito", "ano yun", 
        "sabihin mo", "bigyan mo ako ng info", "pakipaliwanag", 
        "update", "balita", "what is this", "details please", 
        "pakisabi", "can I know", "paano ba", "info naman",

        # Idle or Random Keywords
        "anything else", "ibang bagay", "usapang iba", "idle", 
        "anuman", "random", "walang halaga", "kahit ano", 
        "just talking", "kwentuhan lang", "wala lang", 
        "random topic", "walang kwenta", "random lang", 
        "basta", "bahala na", "kung ano lang", "kung ano ano", 

        # Topic Change
        "change topic", "ibang topic", "ibang usapan", 
        "lipat tayo", "ibang usapin", "move on", "iba naman", 
        "ibang bagay naman", "iba na lang", "shift topic", 
        "let's talk about something else", "palit tayo", 
        "lipat ng topic", "ibang issue", "ibang tanong", 

        # Expressions Indicating End or Pause
        "break muna", "pahinga muna", "stop talking", "pause muna", 
        "wala na akong sasabihin", "wala na", "huwag na lang", 
        "okay na", "ayos na", "that’s it", "yun lang", 
        "wala na akong tanong", "done talking", "done na", 

        # Miscellaneous
        "di ko alam", "ewan", "bahala ka na", "di ako sure", 
        "surprise me", "bahala ka", "ikaw na", "ikaw ang mag-decide", 
        "no idea", "wala akong maisip", "isipin mo na lang", 
        "ikaw na bahala", "paano ba", "ano ulit", "sabihin mo ulit", 
        "walang pakialam", "di mahalaga", "di ko alam ang sasabihin"
    ]

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


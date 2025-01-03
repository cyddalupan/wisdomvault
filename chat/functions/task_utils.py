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
        "cut conversation", "break muna", "pahinga muna",

        # General Help or Assistance
        "help", "kailangan ko ng tulong", "assist", "assistance", 
        "support", "query", "tanong", "general question", "tulong", 
        "help me", "can you assist", "paano ito", "help naman", 
        "ano gagawin", "assist me", "may tanong ako", "can you help", 
        "can you explain", "kailangan ng paliwanag", "paassist", 
        "ano na", "ano meron", "help mo ako", "explain naman", 

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
        "chit chat", "gusto lang magkwento", "wala lang", "usapang walang kwenta", 

        # Topic Change
        "change topic", "ibang topic", "ibang usapan", 
        "lipat tayo", "ibang usapin", "move on", "iba naman", 
        "ibang bagay naman", "iba na lang", "shift topic", 
        "lets talk about something else", "palit tayo", 
        "lipat ng topic", "ibang issue", "ibang tanong", 
        "magsimula ulit", "shift the conversation", "lets change topic",

        # Expressions Indicating End or Pause
        "break muna", "pahinga muna", "stop talking", "pause muna", 
        "wala na akong sasabihin", "wala na", "huwag na lang", 
        "okay na", "ayos na", "thats it", "yun lang", 
        "wala na akong tanong", "done talking", "done na", 
        "Im done", "tapusin na", "stop for now", 

        # Miscellaneous
        "di ko alam", "ewan", "bahala ka na", "di ako sure", 
        "surprise me", "bahala ka", "ikaw na", "ikaw ang magdecide", 
        "no idea", "wala akong maisip", "isipin mo na lang", 
        "ikaw na bahala", "paano ba", "ano ulit", "sabihin mo ulit", 
        "walang pakialam", "di mahalaga", "di ko alam ang sasabihin",
        "I dont know", "wala akong alam", "pwedeng bang magchange topic?",

        # System Tutorial
        "system tutorial", "how does this work", "what can you do", "how do you use this", 
        "teach me", "guide me", "how to use", "paano gamitin", "paano ito gumagana", 
        "how can you assist", "what can I ask", "ano ang kaya mong gawin", 
        "ano ang pwede kong itanong", "tutorial", "system guide", "system help",

        # App Info
        "app info", "about the app", "what is this app", "what is this system", 
        "tell me about the system", "what do you do", "who created you", "what can this app do", 
        "chatbot info", "about chatbot", "about assistant", "what is chatbot", "what is this assistant", 
        "tell me about the assistant", "sino gumawa nito", "ano ba ang app na ito",

        # Storage/Database/Google Sheets Usage
        "where is my data stored", "where do you store data", "data storage", 
        "storage location", "where is the information saved", "where is my information", 
        "why use google sheets", "why store data in google sheets", "what's with google sheets", 
        "how is my data saved", "how is my data stored", "google sheets as storage", 
        "why google sheets", "data in google sheets", "is google sheets safe", 
        "is my data secure", "can I access my data", "how to access my data", "where can I see my data", 
        "google sheets database", "google sheets storage", "how is google sheets used here",

        # Privacy/Security of Data
        "is my data private", "is my data safe", "privacy", "data security", 
        "who can see my data", "who has access to my data", "how secure is this", 
        "can anyone access my data", "data privacy policy", "privacy policy", "is it safe to use", 
        "how do you protect my data", "how do you protect user data", "your data safety",
        
        # General Technology Questions
        "how does it work", "how does the system work", "what is this system built on", 
        "what technology is used", "how is this developed", "what is the backend of this system", 
        "what's behind this system", "what platform is this app", "what's this built on",
        
        # Google Sheets Features
        "google sheets features", "what does google sheets offer", "how does google sheets help", 
        "why google sheets over other databases", "what makes google sheets useful", "how google sheets works",
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
        # Check if the normalized message exactly matches any keyword
        if normalized_message in [keyword.lower() for keyword in keywords]:
            print("MANUAL CHANGE", task)
            return task

    return None



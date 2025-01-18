import requests

def send_message(recipient_id, message_text, facebook_page_instance):
    if facebook_page_instance.token == "antoken":
        print("recipient_id", recipient_id)
        print("message_text", message_text)
        print("facebook_page_instance", facebook_page_instance)
        return None
    post_url = f"https://graph.facebook.com/v11.0/me/messages?access_token={facebook_page_instance.token}"
    response_message = {
        'recipient': {'id': recipient_id},
        'message': {'text': message_text}
    }
    response = requests.post(post_url, json=response_message)
    return response.status_code
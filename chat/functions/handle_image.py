from chat.models import Chat, UserProfile
from chat.utils import send_image, send_message


def handle_image(message, user_profile, sender_id, facebook_page_instance):
    for attachment in message.get('attachments', []):
        if attachment.get('type') == 'image':
            image_url = attachment.get('payload', {}).get('url')
            if image_url:
                message_text = "[User Sends Image]"
                response_text = "Salamat, May iba ka pa bang kailangan? 😊"
                Chat.objects.create(user=user_profile, message=message_text, reply=response_text)
                send_message(sender_id, response_text, facebook_page_instance)

                # Fetch all admins for the page
                admin_users = UserProfile.objects.filter(page_id=user_profile.page_id, user_type='admin')
                # Loop through all admins and send them a message
                message_admin = f"{user_profile.name} sent an image 📷. This is a posible payment, Confirm on Google Sheets. Thank you! 😊" + (f" User's SMS is {user_profile.sms}" if user_profile.sms else "")
                for admin in admin_users:
                    Chat.objects.create(user=admin, message='', reply=message_admin)
                    send_image(admin.facebook_id, image_url, facebook_page_instance)
                    send_message(
                        admin.facebook_id,
                        message_admin,
                        facebook_page_instance
                    )
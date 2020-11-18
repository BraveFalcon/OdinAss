import vk
import random


class Bot:
    def __init__(self):
        self.session = vk.Session(access_token=open("key.txt").read().strip())
        self.api = vk.API(self.session)
        self.vk_version = "5.103"
    
    def get_user(self, user_id):
        return self.api.users.get(
            v=self.vk_version,
            user_id=user_id
        )
    
    def send(self, user, message, *args, **kwargs):
        return self.api.messages.send(
            v=self.vk_version,
            peer_id=user.id,
            random_id=random.random(),
            message=message,
            *args, **kwargs
        )
    
    def get_conversations(self, filter="unread"):
        return self.api.messages.getConversations(
            v=self.vk_version,
            filter=filter
        )
    
    def get_history(self, peer_id, start_message, count):
        return self.api.messages.getHistory(
            v=self.vk_version,
            peer_id=peer_id,
            start_message_id=start_message,
            count=count,
        )
    
    def get_messages(self, message_ids):
        return self.api.messages.getById(
            v=self.vk_version,
            message_ids=message_ids
        )['items']
    
    def mark_as_read(self, peer_id):
        return self.api.messages.markAsRead(
            v=self.vk_version,
            peer_id=peer_id
        )

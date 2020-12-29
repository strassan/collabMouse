import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer


class MouseConsumer(WebsocketConsumer):
    def connect(self):
        self.group_name = "main_group"
        num_of_connections = getattr(self.channel_layer, self.group_name, 0)
        if not num_of_connections:
            setattr(self.channel_layer, self.group_name, 1)
        else:
            setattr(self.channel_layer, self.group_name, num_of_connections + 1)

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )

        self.user_id = getattr(self.channel_layer, self.group_name, 0)

        self.accept()

    def disconnect(self, close_code):
        num_of_connections = getattr(self.channel_layer, self.group_name, 0)
        setattr(self.channel_layer, self.group_name, num_of_connections - 1)
        if num_of_connections == 1:
            delattr(self.channel_layer, self.group_name)

        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        pos = (text_data_json['posX'], text_data_json['posY'])

        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {
                'type': 'mouse_movement',
                'num_of_users': getattr(self.channel_layer, self.group_name, 0),
                'user_id': self.user_id,
                'posX': pos[0],
                'posY': pos[1],
            }
        )

    def mouse_movement(self, event):
        num_of_users = event['num_of_users']
        user_id = event['user_id']
        pos = (event['posX'], event['posY'])

        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'num_of_users': num_of_users,
            'user_id': user_id,
            'posX': pos[0],
            'posY': pos[1],
        }))

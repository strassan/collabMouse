import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from copy import deepcopy


class MouseConsumer(WebsocketConsumer):
    def connect(self):
        self.group_name = "main_group"
        connected_users = getattr(self.channel_layer, self.group_name + '_users', [])
        if not connected_users:
            self.user_id = 0
            setattr(self.channel_layer, self.group_name + '_users', [{
                'userID': self.user_id,
                'last_mouse_pos': (0, 0),
            }])
            connected_users = getattr(self.channel_layer, self.group_name + '_users', [])
        else:
            user_ids = [d['userID'] for d in connected_users]
            self.user_id = max(user_ids) + 1
            connected_users.append({
                'userID': self.user_id,
                'last_mouse_pos': (0, 0),
            })
            setattr(self.channel_layer, self.group_name + '_users', connected_users)

        # join room group
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        # join user group
        self.user_group_name = self.group_name + '_user' + str(self.user_id)
        async_to_sync(self.channel_layer.group_add)(
            self.user_group_name,
            self.channel_name
        )

        # send all current users mouse positions
        for user in connected_users:
            self.send_mousemoved(pos=user['last_mouse_pos'], user_id=user['userID'], group_name=self.user_group_name)
        # send all current segments
        segments = getattr(self.channel_layer, self.group_name + '_segments', [])
        segments_to_send = []
        for seg in segments:
            s = {
                'userID': seg['userID'],
                'startX': seg['nodes'][0][0],
                'startY': seg['nodes'][0][1],
                'endX': seg['nodes'][1][0],
                'endY': seg['nodes'][1][1]
            }
            segments_to_send.append(s)
        self.send_dumpsegments(segments_to_send)

        self.accept()

    def disconnect(self, close_code):
        connected_users = getattr(self.channel_layer, self.group_name + '_users', [])
        user_ids = [d['userID'] for d in connected_users]
        user_id_index = user_ids.index(self.user_id)
        connected_users.remove(connected_users[user_id_index])
        if len(connected_users) == 0:
            delattr(self.channel_layer, self.group_name + '_users')
        else:
            setattr(self.channel_layer, self.group_name + '_users', connected_users)

        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        event_type = text_data_json['evtType']

        if event_type == 'mousepos':
            pos = (text_data_json['posX'], text_data_json['posY'])

            # update last_mouse_pos
            connected_users = getattr(self.channel_layer, self.group_name + '_users', [])
            user_ids = [d['userID'] for d in connected_users]
            user_id_index = user_ids.index(self.user_id)
            connected_users[user_id_index]['last_mouse_pos'] = pos
            setattr(self.channel_layer, self.group_name + '_users', connected_users)

            self.send_mousemoved(pos)

        elif event_type == 'newsegment':
            nodes = [(text_data_json['startX'], text_data_json['startY']),
                     (text_data_json['endX'], text_data_json['endY'])]

            # add segment to channel_layer
            segments = getattr(self.channel_layer, self.group_name + '_segments', [])
            if not segments:
                setattr(self.channel_layer, self.group_name + '_segments', [{
                    'userID': self.user_id,
                    'nodes': nodes,
                }])
            else:
                segments.append({
                    'userID': self.user_id,
                    'nodes': nodes,
                })
                setattr(self.channel_layer, self.group_name + '_segments', segments)

            self.send_drawsegment(nodes)

        elif event_type == 'clearall':
            # remove all segments from channel_layer
            delattr(self.channel_layer, self.group_name + '_segments')
            self.send_clearall()

        else:
            pass

    def send_mousemoved(self, pos, user_id=None, group_name=None):
        if user_id is None:
            user_id = self.user_id
        if group_name is None:
            group_name = self.group_name

        async_to_sync(self.channel_layer.group_send)(
            group_name,
            {
                'type': 'mousemoved_type',
                'userID': user_id,
                'posX': pos[0],
                'posY': pos[1],
            }
        )

    def mousemoved_type(self, event):
        json_dump = deepcopy(event)
        json_dump['evtType'] = 'mousemoved'
        json_dump.pop('type', None)

        self.send(text_data=json.dumps(json_dump))

    def send_drawsegment(self, nodes, user_id=None, group_name=None):
        if user_id is None:
            user_id = self.user_id
        if group_name is None:
            group_name = self.group_name

        async_to_sync(self.channel_layer.group_send)(
            group_name,
            {
                'type': 'drawsegment_type',
                'userID': user_id,
                'startX': nodes[0][0],
                'startY': nodes[0][1],
                'endX': nodes[1][0],
                'endY': nodes[1][1],
            }
        )

    def drawsegment_type(self, event):
        json_dump = deepcopy(event)
        json_dump['evtType'] = 'drawsegment'
        json_dump.pop('type', None)

        self.send(text_data=json.dumps(json_dump))

    def send_clearall(self):
        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {
                'type': 'clearall_type',
            }
        )

    def clearall_type(self, event):
        json_dump = deepcopy(event)
        json_dump['evtType'] = 'clearall'
        json_dump.pop('type', None)

        self.send(text_data=json.dumps(json_dump))

    def send_dumpsegments(self, segments):
        async_to_sync(self.channel_layer.group_send)(
            self.user_group_name,
            {
                'type': 'dumpsegments_type',
                'list': segments,
            }
        )

    def dumpsegments_type(self, event):
        json_dump = deepcopy(event)
        json_dump['evtType'] = 'dumpsegments'
        json_dump.pop('type', None)

        self.send(text_data=json.dumps(json_dump))

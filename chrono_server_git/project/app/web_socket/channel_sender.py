import asyncio
from channels.layers import get_channel_layer

channel_layer = get_channel_layer()


async def send_tag(control_point_id, sequence, tag, time, ignored, by_hand, description):
    await channel_layer.group_send(
        f'point_{control_point_id}',
        {
            'type': 'ws_tag',
            'control_point_id': control_point_id,
            'sequence': sequence,
            'tag': tag,
            'time': time,
            'ignored': ignored,
            'by_hand': by_hand,
            'description': description
        }
    )



# async def send_tag(date_time, counter, tag):
#     await channel_layer.group_send(
#         'live',
#         {
#             'type': 'w_tag',
#             'date_time': date_time,
#             'counter': counter,
#             'tag': tag
#         }
#     )

# async def send_status(date_time, status):
#     await channel_layer.group_send(
#         'live',
#         {
#             'type': 'w_status',
#             'date_time': date_time,
#             'status': status,
#         }
#     )
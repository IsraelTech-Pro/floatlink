from django.urls import path

from . import views

app_name = "float_requests"

urlpatterns = [
    path("create/", views.create_request, name="create"),
    path("nearby/", views.nearby_agents, name="nearby"),
    path("ecash/", views.ecash_agents, name="ecash_agents"),
    path("incoming/poll/", views.incoming_poll, name="incoming_poll"),
    path("incoming/feed/", views.incoming_feed, name="incoming_feed"),
    path("notifications/poll/", views.notifications_poll, name="notifications_poll"),
    path("notifications/<int:pk>/ack/", views.notification_ack, name="notification_ack"),
    path("chats/", views.chat_history, name="chat_history"),
    path("my/", views.my_requests, name="my"),
    path("incoming/", views.incoming_requests, name="incoming"),
    path("<int:pk>/", views.request_detail, name="detail"),
    path("<int:pk>/messages/", views.request_messages, name="messages"),
    path("<int:pk>/messages/send/", views.send_message, name="send_message"),
    path("<int:pk>/accept/", views.accept_request, name="accept"),
    path("<int:pk>/decline/", views.decline_request, name="decline"),
    path("<int:pk>/cancel/", views.cancel_request, name="cancel"),
    path("<int:pk>/complete/", views.complete_request, name="complete"),
]

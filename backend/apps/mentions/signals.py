"""
Mention signal.

Fired once per newly created mention. The notifications app connects a receiver
here so a mention produces an in-app notification, without mentions needing to
know notifications exist.

Receiver signature:
    def handler(sender, mention, comment, actor, recipient, **kwargs): ...
"""

from django.dispatch import Signal

user_mentioned = Signal()

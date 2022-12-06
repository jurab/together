
from api.registry import get_global_registry

# Import schema files from newly registered apps
# Sorted from core apps to more dependent apps, NOT ALPHABETICALLY
from users.schema import *
from locations.schema import *
from organisations.schema import *
from posts.schema import *
from events.schema import *
from chats.schema import *


schema = get_global_registry().get_schema()

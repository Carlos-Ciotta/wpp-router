from enum import Enum
class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACTS = "contacts"
    INTERACTIVE = "interactive"
    BUTTON = "button"
    REACTION = "reaction"
    ORDER = "order"
    SYSTEM = "system"
    UNKNOWN = "unknown"

    @property
    def is_media(self) -> bool:
        return self in (self.IMAGE, self.VIDEO, self.AUDIO, self.DOCUMENT, self.STICKER)
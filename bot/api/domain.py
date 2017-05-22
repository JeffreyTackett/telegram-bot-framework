class ApiObject:
    def __init__(self, _type=None, **data):
        self._type = _type
        self.data = data

    def get_type(self):
        return self._type

    def get_or_fail(self, key):
        value = self.data[key]
        return self.wrap_api_object(value)

    def get_or_default(self, key, default=None):
        value = self.data.get(key, default)
        return self.wrap_api_object(value)

    def __getattr__(self, item):
        if len(item) > 1 and item[-1] == "_":
            item = item[:-1]
        return self.get_or_default(item)

    @staticmethod
    def wrap_api_object(data):
        if type(data) is dict:
            return ApiObject(**data)
        elif type(data) is list:
            return ApiObjectList(data)
        else:
            return data


class ApiObjectList:
    def __init__(self, data_list: list):
        self.data_list = data_list

    def __iter__(self):
        return self.__wrapped_api_objects()

    def __wrapped_api_objects(self):
        for data in self.data_list:
            yield ApiObject.wrap_api_object(data)


class OutApiObject(ApiObject):
    LOCAL_PARAM_ERROR_CALLBACK = "__error_callback"
    LOCAL_PARAMS = [LOCAL_PARAM_ERROR_CALLBACK]

    def with_error_callback(self, func):
        self.data[self.LOCAL_PARAM_ERROR_CALLBACK] = func
        return self


class Message(OutApiObject):
    def to_chat(self, chat=None, message=None, chat_id=None):
        if message is not None:
            chat = message.chat
        if chat is not None:
            chat_id = chat.id
        self.data["chat_id"] = chat_id
        return self

    def reply_to_message(self, message=None, message_id=None):
        if message is not None:
            message_id = message.message_id
        self.data["reply_to_message_id"] = message_id
        return self

    def to_chat_replying(self, message):
        self.to_chat(message=message)
        self.reply_to_message(message)
        return self

    @staticmethod
    def create(text, chat_id=None, **kwargs):
        return Message(_type=Message, text=text, chat_id=chat_id, **kwargs)

    @staticmethod
    def create_reply(message, reply_text):
        return Message.create(reply_text).to_chat(message=message).reply_to_message(message)


class CaptionableMessage(Message):
    def with_caption(self, caption_text):
        self.data["caption"] = caption_text
        return self


class Photo(CaptionableMessage):
    @staticmethod
    def create_photo(file_id):
        return Photo(_type=Photo, photo=file_id)


class Sticker(Message):
    @staticmethod
    def create_sticker(file_id):
        return Sticker(_type=Sticker, sticker=file_id)


class Document(CaptionableMessage):
    @staticmethod
    def create_document(file_id):
        return Document(_type=Document, document=file_id)


class Voice(CaptionableMessage):
    @staticmethod
    def create_voice(file_id):
        return Voice(_type=Voice, voice=file_id)


class VideoNote(Message):
    @staticmethod
    def create_video_note(file_id, length):
        # for some reason, api fails if length is not provided, although it is an optional field
        return VideoNote(_type=VideoNote, video_note=file_id, length=length)


class Audio(CaptionableMessage):
    @staticmethod
    def create_audio(file_id):
        return Voice(_type=Audio, audio=file_id)


class Video(CaptionableMessage):
    @staticmethod
    def create_video(file_id):
        return Voice(_type=Video, video=file_id)


class MessageEntityParser:
    def __init__(self, message):
        self.text_as_utf16_bytes = message.text.encode("utf-16")

    def get_entity_text(self, entity):
        start_byte = 2 + entity.offset * 2  # BOM + characters * 2 bytes
        end_byte = start_byte + entity.length * 2
        return self.text_as_utf16_bytes[start_byte:end_byte].decode("utf-16")

    def get_text_after_entity(self, entity):
        start_byte = 2 + (entity.offset + entity.length) * 2
        return self.text_as_utf16_bytes[start_byte:].decode("utf-16")

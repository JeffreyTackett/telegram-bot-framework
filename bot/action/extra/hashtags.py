import collections

from bot.action.core.action import Action
from bot.action.core.command import CommandUsageMessage
from bot.action.userinfo import UserStorageHandler
from bot.action.util.format import DateFormatter, UserFormatter
from bot.api.domain import Message, MessageEntityParser


class SaveHashtagsAction(Action):
    def process(self, event):
        hashtag_entities = self.get_hashtag_entities(event.message.entities)
        if len(hashtag_entities) > 0:
            new_hashtags = self.get_message_hashtags(event.message, hashtag_entities)
            if not new_hashtags.is_empty():
                HashtagStorageHandler(event).save_new_hashtags(new_hashtags)

    @staticmethod
    def get_hashtag_entities(entities):
        return [entity for entity in entities if entity.type == "hashtag"] if entities is not None else []

    def get_message_hashtags(self, message, hashtag_entities):
        entity_parser = MessageEntityParser(message)
        hashtags = HashtagList([])
        for entity in hashtag_entities:
            hashtag = self.get_hashtag_from_entity(message, entity, entity_parser)
            hashtags.add(hashtag)
        return hashtags

    @staticmethod
    def get_hashtag_from_entity(message, entity, entity_parser):
        hashtag = entity_parser.get_entity_text(entity)
        user_id = message.from_.id if message.from_ is not None else "-"
        return Hashtag(hashtag, message.date, user_id)


class ListHashtagsAction(Action):
    def process(self, event):
        action, number_of_hashtags_to_display, help_args = self.parse_args(event.command_args.split())
        if action in ("recent", "popular"):
            hashtags = HashtagStorageHandler(event).get_stored_hashtags()
            if hashtags.is_empty():
                response = self.get_response_empty()
            elif action == "recent":
                response = self.get_response_recent(event, hashtags, number_of_hashtags_to_display)
            else:
                response = self.get_response_popular(event, hashtags, number_of_hashtags_to_display)
        else:
            response = self.get_response_help(event, help_args)
        self.api.send_message(response.replying_to(event.message))

    @staticmethod
    def parse_args(args):
        action = "help"
        number_of_hashtags_to_display = 10
        help_args = args[1:]
        if len(args) == 0:
            action = "recent"
        elif len(args) == 1:
            if args[0].isnumeric():
                action = "recent"
                number_of_hashtags_to_display = int(args[0])
            else:
                action = args[0]
        elif len(args) == 2:
            if args[1].isnumeric():
                number_of_hashtags_to_display = int(args[1])
                action = args[0]
        return action, number_of_hashtags_to_display, help_args

    @staticmethod
    def get_response_help(event, help_args):
        args = ["[number_of_hashtags]", "popular [number_of_hashtags]"]
        description = "By default, display recent hashtags.\n\n" \
                      "Use *popular* to show most popular ones.\n\n" \
                      "You can also add a number to the end in both modes to limit the hashtags to display" \
                      " (default is 10)."
        return CommandUsageMessage.get_usage_message(event.command, args, description)

    @staticmethod
    def get_response_empty():
        return Message.create("I have not seen any hashtag in this chat.\n"
                              "Write some and try again (hint: #ThisIsAHashTag).")

    def get_response_recent(self, event, hashtags, number_of_hashtags_to_display):
        user_storage_handler = UserStorageHandler.get_instance(self.state)
        sorted_hashtags = hashtags.sorted_by_recent_use(number_of_hashtags_to_display)
        printable_hashtags = sorted_hashtags.printable_version(user_storage_handler)
        return self.__build_success_response_message(event, "Most recent hashtags:", printable_hashtags)

    def get_response_popular(self, event, hashtags, number_of_hashtags_to_display):
        printable_hashtags = hashtags.grouped_by_popularity(number_of_hashtags_to_display).printable_version()
        return self.__build_success_response_message(event, "Most popular hashtags:", printable_hashtags)

    @staticmethod
    def __build_success_response_message(event, title, printable_hashtags):
        footer = "\n\nUse *" + event.command + " help* to see more options."
        return Message.create(title + "\n" + printable_hashtags + footer, parse_mode="Markdown")


class Hashtag:
    def __init__(self, hashtag, date=None, user_id=None):
        self.hashtag = hashtag
        self.date = date
        self.user_id = user_id

    def printable_version(self, user_storage_handler):
        formatted_date = DateFormatter.format(self.date) if self.date is not None else "???"
        formatted_user = UserFormatter.retrieve_and_format(self.user_id, user_storage_handler) if self.user_id is not None else "???"
        return "%s  (%s by %s)" % (self.hashtag, formatted_date, formatted_user)

    def serialize(self):
        return "%s %s %s\n" % (self.hashtag, self.date, self.user_id)

    @staticmethod
    def deserialize(hashtag_data):
        return Hashtag(*hashtag_data.split(" "))


class HashtagList:
    def __init__(self, hashtags):
        self.hashtags = hashtags

    def add(self, hashtag: Hashtag):
        self.hashtags.append(hashtag)

    def is_empty(self):
        return len(self.hashtags) == 0

    def grouped_by_popularity(self, max_to_return):
        hashtags_names = (hashtag.hashtag for hashtag in self.hashtags)
        return HashtagGroup(collections.Counter(hashtags_names).most_common(max_to_return))

    def sorted_by_recent_use(self, limit):
        if limit <= 0:
            return HashtagList([])
        # for now, assume they are already sorted by date
        return HashtagList(reversed(self.hashtags[-limit:]))

    def printable_version(self, user_storage_handler):
        return "\n".join((hashtag.printable_version(user_storage_handler) for hashtag in self.hashtags))

    def serialize(self):
        return "".join((hashtag.serialize() for hashtag in self.hashtags))

    @staticmethod
    def deserialize(hashtags_data):
        return HashtagList([Hashtag.deserialize(hashtag) for hashtag in hashtags_data.splitlines()])


class HashtagGroup:
    def __init__(self, grouped_hashtags):
        self.grouped_hashtags = grouped_hashtags

    def printable_version(self):
        return "\n".join(("%s -> %s" % (count, hashtag) for hashtag, count in self.grouped_hashtags))


class HashtagStorageHandler:
    def __init__(self, event):
        self.event = event

    def get_stored_hashtags(self):
        hashtags = self.event.state.hashtags
        if hashtags is None:
            hashtags = ""
        return HashtagList.deserialize(hashtags)

    def save_new_hashtags(self, hashtags: HashtagList):
        self.event.state.set_value("hashtags", hashtags.serialize(), append=True)

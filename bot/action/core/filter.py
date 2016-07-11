from bot.action.core.action import IntermediateAction


class TextMessageAction(IntermediateAction):
    def process(self, event):
        text = event.message.text
        if text is not None:
            event.text = text
            self._continue(event)


class EditedMessageAction(IntermediateAction):
    def process(self, event):
        edited_message = event.update.edited_message
        if edited_message is not None:
            event.message = edited_message
            event.edited_message = edited_message
            event.chat = edited_message.chat
            self._continue(event)


class MessageAction(IntermediateAction):
    def process(self, event):
        message = event.update.message
        if message is not None:
            event.message = message
            event.chat = message.chat
            self._continue(event)


class NoPendingAction(IntermediateAction):
    def process(self, event):
        if not event.is_pending:
            self._continue(event)

class CreateMessagesWithConversationHistoryError(Exception):
    def __init__(self, message: str, original_exception: Exception):
        super().__init__(message)
        self.original_exception = original_exception

from datetime import datetime

import telebot
import utils
import config

TELEGRAM_TOKEN: str = utils.load_confidentials_from_env("TELEGRAM_TOKEN")
ADMIN_ID: str = utils.load_confidentials_from_env("ADMIN_ID")


class BetBot(telebot.TeleBot):

    def __init__(self):
        super().__init__(token=TELEGRAM_TOKEN, parse_mode='HTML')
        self.register_message_handler(callback=self.handle_message, func=self.message_filter)
        self.start()

    def start(self) -> None:
        self.notify_admin("<b>БОТ ЗАПУЩЕН</b>")
        try:
            self.polling(none_stop=True)
        except Exception as e:
            self.notify_admin(f"<b>БОТ ОСТАНОВЛЕН</b>\n\nНеожиданная ошибка: {e}")
        else:
            self.notify_admin("<b>БОТ ОСТАНОВЛЕН</b>\n\nВозможная причина: принудительное завершение из IDE.")

    def notify_admin(self, text: str) -> None:
        prefix = datetime.now().strftime(config.PREFERRED_DATETIME_FORMAT) + "\n"
        self.send_message(chat_id=ADMIN_ID, text=prefix + text, parse_mode='HTML')

    def handle_message(self, message: telebot.types.Message) -> None:
        """Handles all text messages recieved by auth users."""
        text = f"A message has been received\n" \
               f"Sender: {message.from_user.first_name} {message.from_user.last_name}\n" \
               f"Text: {message.text}"
        self.notify_admin(text=text)

    def message_filter(self, message: telebot.types.Message) -> bool:
        """
        Filter for all messages coming from users. Declines unauthorized users and all non-text messages.
        Sends replies describing the situation to message senders.

        :param message: The incoming message object from a user.
        :return: True if a message is allowed to be processed by bot, False otherwise.
        """

        message_is_text = message.content_type == 'text'

        if not self.user_authorized(message.from_user.id):
            self.reply_to(message=message,
                          text=f"<b>Доступ запрещен!</b>\n\n"
                               f"К сожалению, это закрытое соревнование, и Вы не являетесь его участником. 😢"
                          )
            return False
        if not message_is_text:
            self.reply_to(message=message, text=f"<b>Ой!</b>\nЭтот бот понимает только текстовые сообщения.")
            return False
        return True

    @staticmethod
    def user_authorized(user_id: int) -> bool:
        return user_id == int(ADMIN_ID)


if __name__ == "__main__":
    bot = BetBot()

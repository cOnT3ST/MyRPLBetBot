from datetime import datetime

import telebot
import utils
import config

TELEGRAM_TOKEN: str = utils.load_confidentials_from_env("TELEGRAM_TOKEN")
ADMIN_ID: str = utils.load_confidentials_from_env("ADMIN_ID")


class BetBot(telebot.TeleBot):

    def __init__(self):
        super().__init__(token=TELEGRAM_TOKEN, parse_mode=None)
        self.register_message_handler(callback=self.handle_message, func=self.filter_users)

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
        text = f"A message has been received\n" \
                 f"Sender: {message.from_user.first_name} {message.from_user.last_name}\n" \
                 f"Text: {message.text}"
        self.notify_admin(text=text)

    def filter_users(self, message: telebot.types.Message) -> bool:
        """
        Checks if the user is authorized and sends a denial message if not. Used as a filter for message handling.

        :param message: The incoming message object from a user.
        :return: True if user is authorized, False otherwise.
        """
        user_authorized = message.from_user.id == int(ADMIN_ID)
        if not user_authorized:
            user_id = message.from_user.id
            self.send_message(chat_id=user_id,
                              parse_mode='HTML',
                              text='<b>Доступ запрещен!</b>\n\n'
                                   'К сожалению, это закрытое соревнование, и Вы не являетесь его участником. 😢')
        return user_authorized


if __name__ == "__main__":
    bot = BetBot()
    bot.start()

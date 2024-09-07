from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from datetime import timedelta
from sqlalchemy.exc import NoResultFound, IntegrityError
from telegram.ext import (
    Application as TelegramApplication,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from ipbes_notifier.utils import batched
from sqlmodel import select, and_
from sqlalchemy.orm import selectinload
from ipbes_notifier.chat import Chat
from ipbes_notifier.subscription import Subscription
from ipbes_notifier.topic import Topic


class Application:
    def __init__(
        self,
        *,
        db_sessionmaker: async_sessionmaker[AsyncSession],
        poll_interval: timedelta,
        token: str,
    ):
        self._db_sessionmaker = db_sessionmaker

        self._application = TelegramApplication.builder().token(token).build()
        self._application.add_handler(CommandHandler("start", self._start))
        self._application.add_handler(CommandHandler("stop", self._stop))
        self._application.add_handler(CallbackQueryHandler(self._button_callback))
        self._application.job_queue.run_repeating(self._poll, poll_interval, first=5)

    async def __get_topics_selection_keyboard(
        self, chat: Chat, *, db_session: AsyncSession
    ) -> InlineKeyboardMarkup:
        topics = await db_session.execute(
            select(Topic, Subscription)
            .select_from(Topic)
            .outerjoin(
                Subscription,
                and_(
                    Topic.name == Subscription.topic_name,
                    Subscription.chat == chat,
                ),
            )
        )

        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        ("✗ " if subscription is None else "✓ ") + topic.name,
                        callback_data=topic.name,
                    )
                    for (topic, subscription) in line
                ]
                for line in batched(topics, 2)
            ]
        )

    async def _button_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        chat_id = update.effective_message.chat_id

        query = update.callback_query
        await query.answer()

        async with self._db_sessionmaker() as db_session:
            chat = await db_session.get(Chat, chat_id)

            if chat is None:
                await query.edit_message_text(
                    "Subscription is stopped, please /start again"
                )
                return

            topic = await db_session.get(Topic, query.data)

            subscription = await db_session.scalar(
                select(Subscription).where(
                    Subscription.chat == chat,
                    Subscription.topic == topic,
                )
            )

            if subscription is None:
                subscription = Subscription(chat=chat, topic=topic)
                db_session.add(subscription)
            else:
                await db_session.delete(subscription)
            await db_session.commit()

            reply_markup = await self.__get_topics_selection_keyboard(
                chat, db_session=db_session
            )

        await query.edit_message_reply_markup(reply_markup=reply_markup)

    async def _poll(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        async with self._db_sessionmaker() as db_session:
            for topic in await db_session.scalars(
                select(Topic).options(selectinload(Topic.subscriptions))
            ):
                async for new_document in topic.poll():
                    if new_document.symbol:
                        for subscription in topic.subscriptions:
                            await self._application.bot.sendMessage(
                                subscription.chat_id, str(new_document)
                            )

    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_message.chat_id

        async with self._db_sessionmaker() as db_session:
            try:
                chat = Chat(id=chat_id)
                db_session.add(chat)
                await db_session.commit()
                await db_session.refresh(chat)
            except IntegrityError:
                await update.message.reply_text(
                    "You are already subscribed, use /stop first"
                )
                return

            reply_markup = await self.__get_topics_selection_keyboard(
                chat, db_session=db_session
            )

        await update.message.reply_text(
            "Select topics to subscribe:", reply_markup=reply_markup
        )

    async def _stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_message.chat_id

        async with self._db_sessionmaker() as db_session:
            try:
                chat = await db_session.get_one(Chat, chat_id)
                await db_session.delete(chat)
                await db_session.commit()
                await update.message.reply_text(
                    "You are no longer subscribed, use /start to subscribe again"
                )
            except NoResultFound:
                await update.message.reply_text(
                    "You were already not subscribed, use /start to subscribe again"
                )

    def run(self) -> None:
        self._application.run_polling()

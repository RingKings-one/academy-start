from aiogram import Dispatcher

from app.bot.handlers import start, common, parent, coach, admin, text_fsm, menu_reply


def setup_routers(dp: Dispatcher) -> None:
    dp.include_router(start.router)
    dp.include_router(common.router)
    dp.include_router(text_fsm.router)
    dp.include_router(menu_reply.router)
    dp.include_router(parent.router)
    dp.include_router(coach.router)
    dp.include_router(admin.router)

from aiogram.client.session.aiohttp import AiohttpSession
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

token = "8570809216:AAFPBqxOEmjTXeHEkEpOGPC7DDvsXUT7GIg"

session = AiohttpSession(proxy="http://201.51.20.178:3128")
bot = Bot(token=token, session=session)
dp = Dispatcher(storage=MemoryStorage())

class TaskStates(StatesGroup):
    waiting_for_task_name = State()
    waiting_for_action = State()
    waiting_for_deadline = State()
    waiting_for_reminder_time = State()

users_db = {}

menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⌚ Задачи")],
        [KeyboardButton(text="😊 Профиль")],
    ],
    resize_keyboard=True
)

profile_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📒 Меню")],
        [KeyboardButton(text="⌚ Задачи")],
    ],
    resize_keyboard=True
)

task_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📒 Меню"), KeyboardButton(text="😊 Профиль")],
        [KeyboardButton(text="🗑️ Удалить задачу"), KeyboardButton(text="⏰ Установить напоминание")],
    ],
    resize_keyboard=True
)

welcome_text = """
<b><i>👋 Добро пожаловать в менеджер задач!</i></b>
Здесь вы можете управлять своими задачами:
<blockquote>• Добавлять новые</blockquote>
<blockquote>• Отмечать выполненные</blockquote>
<blockquote>• Удалять ненужные</blockquote>
<blockquote>• Выберите действие</blockquote>
"""

def ensure_user_exists(user_id, username=None):
    if user_id not in users_db:
        users_db[user_id] = {
            "username": username or "Не указано",
            "completed_tasks": 0,
            "tasks": {}
        }
    return users_db[user_id]

@dp.message(F.text.in_(["📒 Меню", "/start"]))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Не указано"
    ensure_user_exists(user_id, username)
    await message.answer(
        welcome_text, 
        parse_mode=ParseMode.HTML,
        reply_markup=menu_keyboard
    )

@dp.message(F.text == "😊 Профиль")
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Не указано"
    user_data = ensure_user_exists(user_id, username)
    
    active_tasks = 0
    for task_data in user_data["tasks"].values():
        if isinstance(task_data, dict):
            if not task_data.get("completed", False):
                active_tasks += 1
        else:
            if not task_data:
                active_tasks += 1
    
    profile_text = (
        f"👤 <b>Профиль пользователя</b>\n\n"
        f"ID: {user_id}\n"
        f"Username: @{user_data['username']}\n"
        f"Выполнено задач: <b>{user_data['completed_tasks']}</b>\n"
        f"Активных задач: <b>{active_tasks}</b>"
    )
    await message.answer(profile_text, parse_mode=ParseMode.HTML, reply_markup=profile_keyboard)

@dp.message(F.text == "⌚ Задачи")
async def show_tasks(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Не указано"
    user_data = ensure_user_exists(user_id, username)
    
    if user_data["tasks"]:
        tasks_text = "📝 <b>Ваши задачи:</b>\n\n"
        for task_name, task_data in user_data["tasks"].items():
            if isinstance(task_data, dict):
                is_completed = task_data.get("completed", False)
                deadline = task_data.get("deadline")
                reminder = task_data.get("reminder")
            else:
                is_completed = task_data
                deadline = None
                reminder = None
            
            status = "✅" if is_completed else "❌"
            tasks_text += f"{status} {task_name}"
            
            if deadline:
                tasks_text += f" (⏰ до: {deadline.strftime('%d.%m.%Y %H:%M')})"
            if reminder:
                tasks_text += f" [🔔 {reminder.strftime('%d.%m.%Y %H:%M')}]"
            tasks_text += "\n"
        
        tasks_text += "\nВведите название задачи для управления:"
    else:
        tasks_text = "📝 У вас пока нет задач. Введите название первой задачи!"

    await message.answer(
        tasks_text, 
        parse_mode=ParseMode.HTML, 
        reply_markup=task_keyboard
    )
    await state.set_state(TaskStates.waiting_for_task_name)
    await state.update_data(delete_mode=False, add_reminder=False)

@dp.message(F.text == "🗑️ Удалить задачу")
async def delete_task_button(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Не указано"
    user_data = ensure_user_exists(user_id, username)
    
    if not user_data["tasks"]:
        await message.answer("❌ У вас нет задач для удаления!", reply_markup=task_keyboard)
        await state.clear()
        return
    
    await message.answer("Введите название задачи, которую хотите удалить:")
    await state.set_state(TaskStates.waiting_for_task_name)
    await state.update_data(delete_mode=True, add_reminder=False)

@dp.message(F.text == "⏰ Установить напоминание")
async def set_reminder_button(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Не указано"
    user_data = ensure_user_exists(user_id, username)
    
    if not user_data["tasks"]:
        await message.answer("❌ У вас нет задач для установки напоминания!", reply_markup=task_keyboard)
        await state.clear()
        return
    
    await message.answer(
        "Введите название задачи, для которой хотите установить напоминание:"
    )
    await state.set_state(TaskStates.waiting_for_task_name)
    await state.update_data(delete_mode=False, add_reminder=True)

@dp.message(TaskStates.waiting_for_task_name)
async def process_task_input(message: types.Message, state: FSMContext):
    task_name = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or "Не указано"
    user_data = ensure_user_exists(user_id, username)

    if task_name in ["📒 Меню", "😊 Профиль", "⌚ Задачи", "🗑️ Удалить задачу", "⏰ Установить напоминание"]:
        await state.clear()
        if task_name == "📒 Меню":
            await cmd_start(message)
        elif task_name == "😊 Профиль":
            await show_profile(message)
        elif task_name == "⌚ Задачи":
            await show_tasks(message, state)
        elif task_name == "🗑️ Удалить задачу":
            await delete_task_button(message, state)
        else:
            await set_reminder_button(message, state)
        return
    
    if not task_name:
        await message.answer("Пожалуйста, введите название задачи.")
        return
    
    data = await state.get_data()
    delete_mode = data.get("delete_mode", False)
    add_reminder = data.get("add_reminder", False)
    
    if delete_mode:
        if task_name in user_data["tasks"]:
            del user_data["tasks"][task_name]
            await message.answer(f"❌ Задача '{task_name}' удалена.")
            await state.clear()
            await show_tasks(message, state)
        else:
            await message.answer(f"❌ Задача '{task_name}' не найдена!")
        return
    
    if add_reminder:
        if task_name in user_data["tasks"]:
            await message.answer(
                f"⏰ Введите дату и время для напоминания о задаче '{task_name}' в формате:\n"
                "ДД.ММ.ГГГГ ЧЧ:ММ\n"
                "Например: 25.12.2026 15:30"
            )
            await state.update_data(current_task_for_reminder=task_name)
            await state.set_state(TaskStates.waiting_for_reminder_time)
        else:
            await message.answer(f"❌ Задача '{task_name}' не найдена!")
        return
    
    if task_name in user_data["tasks"]:
        task_data = user_data["tasks"][task_name]
        if isinstance(task_data, dict):
            is_completed = task_data.get("completed", False)
            deadline = task_data.get("deadline")
            reminder = task_data.get("reminder")
        else:
            is_completed = task_data
            deadline = None
            reminder = None
        
        response = f"📝 Задача '{task_name}' уже существует.\n"
        response += f"Статус: {'✅ Выполнена' if is_completed else '❌ Не выполнена'}\n"
        if deadline:
            response += f"⏰ Дедлайн: {deadline.strftime('%d.%m.%Y %H:%M')}\n"
        if reminder:
            response += f"🔔 Напоминание: {reminder.strftime('%d.%m.%Y %H:%M')}\n"
        response += "\nВыберите действие:\n"
        response += "• 'удалить' — удалить задачу\n"
        response += "• 'выполнено' — отметить как выполненную\n"
        response += "• 'не выполнено' — отметить как невыполненную\n"
        response += "• 'дедлайн' — установить/изменить дедлайн"
        
        await message.answer(response)
        await state.update_data(current_task=task_name)
        await state.set_state(TaskStates.waiting_for_action)
    else:
        await message.answer(
            f"⏰ Введите дату и время дедлайна для задачи '{task_name}' в формате:\n"
            "ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Или введите 'пропустить', если дедлайн не нужен:"
        )
        await state.update_data(new_task_name=task_name)
        await state.set_state(TaskStates.waiting_for_deadline)

@dp.message(TaskStates.waiting_for_deadline)
async def process_deadline_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Не указано"
    user_data = ensure_user_exists(user_id, username)
    data = await state.get_data()
    task_name = data.get("new_task_name")
    
    deadline_input = message.text.strip()
    
    if deadline_input.lower() == "пропустить":
        deadline = None
    else:
        try:
            deadline = datetime.strptime(deadline_input, "%d.%m.%Y %H:%M")
        except ValueError:
            await message.answer(
                "❌ Неверный формат! Используйте ДД.ММ.ГГГГ ЧЧ:ММ\n"
                "Например: 25.12.2026 15:30\n"
                "Или введите 'пропустить':"
            )
            return
    
    user_data["tasks"][task_name] = {
        "completed": False,
        "deadline": deadline,
        "reminder": None
    }
    
    response = f"✅ Задача '{task_name}' добавлена!"
    if deadline:
        response += f"\n⏰ Дедлайн: {deadline.strftime('%d.%m.%Y %H:%M')}"
    
    await message.answer(response)
    await state.clear()
    await show_tasks(message, state)

@dp.message(TaskStates.waiting_for_reminder_time)
async def process_reminder_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Не указано"
    user_data = ensure_user_exists(user_id, username)
    data = await state.get_data()
    task_name = data.get("current_task_for_reminder")
    
    reminder_time_input = message.text.strip()
    
    try:
        reminder_time = datetime.strptime(reminder_time_input, "%d.%m.%Y %H:%M")
        
        if reminder_time <= datetime.now():
            await message.answer("❌ Время напоминания должно быть в будущем!")
            return
        
        if isinstance(user_data["tasks"][task_name], dict):
            user_data["tasks"][task_name]["reminder"] = reminder_time
        else:
            is_completed = user_data["tasks"][task_name]
            user_data["tasks"][task_name] = {
                "completed": is_completed,
                "deadline": None,
                "reminder": reminder_time
            }
        
        await message.answer(f"✅ Напоминание для задачи '{task_name}' установлено на {reminder_time.strftime('%d.%m.%Y %H:%M')}")
        
        asyncio.create_task(send_reminder(user_id, task_name, reminder_time))
        
        await state.clear()
        await show_tasks(message, state)
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат! Используйте ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Например: 25.12.2026 15:30"
        )

@dp.message(TaskStates.waiting_for_action)
async def process_task_action(message: types.Message, state: FSMContext):
    action = message.text.lower().strip()
    data = await state.get_data()
    task_name = data.get("current_task")
    user_id = message.from_user.id
    username = message.from_user.username or "Не указано"
    user_data = ensure_user_exists(user_id, username)
    
    if not task_name:
        await message.answer("❌ Ошибка: задача не найдена")
        await state.clear()
        await show_tasks(message, state)
        return
    
    if task_name not in user_data["tasks"]:
        await message.answer("❌ Задача не найдена в вашем списке!")
        await state.clear()
        await show_tasks(message, state)
        return
    
    task_data = user_data["tasks"][task_name]
    if isinstance(task_data, dict):
        is_completed = task_data.get("completed", False)
    else:
        is_completed = task_data
    
    if action == "удалить":
        del user_data["tasks"][task_name]
        await message.answer(f"❌ Задача '{task_name}' удалена.")
    
    elif action == "выполнено":
        if isinstance(user_data["tasks"][task_name], dict):
            user_data["tasks"][task_name]["completed"] = True
        else:
            user_data["tasks"][task_name] = True
        user_data["completed_tasks"] += 1
        await message.answer(f"🎉 Задача '{task_name}' отмечена как выполненная!")
    
    elif action == "не выполнено":
        if isinstance(user_data["tasks"][task_name], dict):
            user_data["tasks"][task_name]["completed"] = False
        else:
            user_data["tasks"][task_name] = False
        user_data["completed_tasks"] -= 1
        await message.answer(f"📝 Задача '{task_name}' отмечена как невыполненная.")
    
    elif action == "дедлайн":
        await message.answer(
            f"⏰ Введите новый дедлайн для задачи '{task_name}' в формате:\n"
            "ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Или введите 'удалить', чтобы удалить дедлайн:"
        )
        await state.update_data(editing_deadline=True, current_task=task_name)
        await state.set_state(TaskStates.waiting_for_deadline)
        return
    
    else:
        await message.answer(
            "❌ Неизвестное действие. Используйте:\n"
            "• 'удалить' — удалить задачу\n"
            "• 'выполнено' — отметить как выполненную\n"
            "• 'не выполнено' — отметить как невыполненную\n"
            "• 'дедлайн' — установить/изменить дедлайн"
        )
        return
    
    await state.clear()
    await show_tasks(message, state)

async def send_reminder(user_id: int, task_name: str, reminder_time: datetime):
    """Отправляет напоминание о задаче в указанное время"""
    now = datetime.now()
    wait_seconds = (reminder_time - now).total_seconds()
    
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)
        
        user_data = users_db.get(user_id)
        if user_data and task_name in user_data["tasks"]:
            task_data = user_data["tasks"][task_name]
            is_completed = task_data.get("completed", False) if isinstance(task_data, dict) else task_data
            
            if not is_completed:
                try:
                    await bot.send_message(
                        user_id,
                        f"⏰ <b>Напоминание!</b>\n\n"
                        f"Задача: {task_name}\n"
                        f"Дедлайн: {task_data.get('deadline', {}).strftime('%d.%m.%Y %H:%M') if isinstance(task_data, dict) and task_data.get('deadline') else 'Не установлен'}\n\n"
                        f"Не забудьте выполнить задачу!",
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    print(f"Ошибка отправки напоминания: {e}")

async def check_overdue_tasks():
    """Периодическая проверка просроченных задач"""
    while True:
        now = datetime.now()
        for user_id, user_data in users_db.items():
            for task_name, task_data in user_data["tasks"].items():
                if isinstance(task_data, dict):
                    is_completed = task_data.get("completed", False)
                    deadline = task_data.get("deadline")
                    
                    if not is_completed and deadline and deadline < now:
                        try:
                            await bot.send_message(
                                user_id,
                                f"⚠️ <b>Задача просрочена!</b>\n\n"
                                f"Задача: {task_name}\n"
                                f"Дедлайн: {deadline.strftime('%d.%m.%Y %H:%M')}\n\n"
                                f"Срочно выполните задачу!",
                                parse_mode=ParseMode.HTML
                            )
                        except Exception as e:
                            print(f"Ошибка отправки уведомления о просрочке: {e}")
        
        await asyncio.sleep(60)  

@dp.message(F.text)
async def handle_unknown_text(message: types.Message):
    user_id = message.from_user.id
    if user_id in users_db:
        await message.answer(
            "❓ Пожалуйста, используйте кнопки меню для навигации.",
            reply_markup=menu_keyboard
        )
    else:
        await cmd_start(message)

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🤖 Бот запущен!")

    asyncio.create_task(check_overdue_tasks())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
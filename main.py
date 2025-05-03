import logging
import sqlite3
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
TOKEN = '8051065968:AAHNC7qlJoMnxu5MP10O-xeQ8HZGHNV-LaU'
DB = 'db.sqlite'
QR_IMAGE = 'https://t.me/plinkkkkkkkkk/56'

# States
SELECT_TYPE_STATE, SELECT_OFFER_STATE, ASK_USERNAME, ASK_PHONE, ASK_TXID = range(5)

# DB Setup
def init_db():
    with sqlite3.connect(DB) as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY,
                type TEXT,
                name TEXT,
                img TEXT
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                user_id INT,
                username TEXT,
                phone TEXT,
                offer TEXT,
                txid TEXT,
                status TEXT DEFAULT "pending",
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Add 'type' column if it doesn't exist
        try:
            db.execute("SELECT type FROM offers LIMIT 1")
        except sqlite3.OperationalError:
            db.execute("ALTER TABLE offers ADD COLUMN type TEXT")
            db.commit()

        # Check if the timestamp column exists in orders and add it if not
        try:
            db.execute("SELECT timestamp FROM orders LIMIT 1")
        except sqlite3.OperationalError:
            db.execute("ALTER TABLE orders ADD COLUMN timestamp DATETIME DEFAULT CURRENT_TIMESTAMP")
            db.commit()

        # Insert the provided offer data if the table is empty
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM offers")
        if cursor.fetchone()[0] == 0:
            offers_data = [
                (1, 'Followers', 'Indian Followers 100', 'https://t.me/plinkkkkkkkkk/42'),
                (2, 'Followers', 'Indian Followers 500', 'https://t.me/plinkkkkkkkkk/43'),
                (3, 'Followers', 'Indian Followers 1000', 'https://t.me/plinkkkkkkkkk/44'),
                (4, 'Followers', 'Malayali Followers 100', 'https://t.me/plinkkkkkkkkk/45'),
                (5, 'Followers', 'Malayali Followers 500', 'https://t.me/plinkkkkkkkkk/46'),
                (6, 'Followers', 'Malayali Followers 1000', 'https://t.me/plinkkkkkkkkk/47'),
                (7, 'Followers', 'Standard Followers 100', 'https://t.me/plinkkkkkkkkk/48'),
                (8, 'Followers', 'Standard Followers 500', 'https://t.me/plinkkkkkkkkk/49'),
                (9, 'Followers', 'Standard Followers 1000', 'https://t.me/plinkkkkkkkkk/50'),
                (10, 'Views', 'Standard Views 1k', 'https://t.me/plinkkkkkkkkk/52'),
                (11, 'Views', 'Standard Views 10k', 'https://t.me/plinkkkkkkkkk/51'),
                (12, 'Likes', 'Regular Likes 1k', 'https://t.me/plinkkkkkkkkk/54'),
                (13, 'Likes', 'Regular Likes 10k', 'https://t.me/plinkkkkkkkkk/53')
            ]
            cursor.executemany("INSERT INTO offers (id, type, name, img) VALUES (?, ?, ?, ?)", offers_data)
            db.commit()

        db.commit()

# ===================== USER FUNCTIONS =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command handler showing category buttons"""
    keyboard = [
        [InlineKeyboardButton("Get Followers", callback_data='category:Followers')],
        [InlineKeyboardButton("Get Likes", callback_data='category:Likes')],
        [InlineKeyboardButton("Get Views", callback_data='category:Views')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        '👋 <b>Welcome! Please select a service type:</b>',
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return SELECT_TYPE_STATE

async def select_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the selection of a service type"""
    query = update.callback_query
    await query.answer()
    service_type = query.data.split(':')[1]
    context.user_data['service_type'] = service_type

    with sqlite3.connect(DB) as db:
        offers = db.execute('SELECT name, img FROM offers WHERE type=?', (service_type,)).fetchall()

    if not offers:
        await query.message.reply_text(f'📭 <b>No offers available for {service_type} at the moment.</b>', parse_mode='HTML')
        return ConversationHandler.END

    await query.message.reply_text(f'🎁 <b>Available offers for {service_type}:</b>', parse_mode='HTML')
    for name, img in offers:
        btn = InlineKeyboardMarkup([[InlineKeyboardButton(f"🛒 {name}", callback_data=f'select:{name}')]])
        try:
            await query.message.reply_photo(
                photo=img,
                caption=f"<b>{name}</b>",
                reply_markup=btn,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error sending photo for {name}: {e}")
            await query.message.reply_text(f"⚠️ Error displaying offer: {name}. Please try again later.", parse_mode='HTML')
    return SELECT_OFFER_STATE

async def select_offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle offer selection"""
    query = update.callback_query
    await query.answer()

    context.user_data['offer'] = query.data.split(':')[1]
    await query.message.reply_text(
        '📝 <b>Please send your Instagram profile link or username:</b>\n\n',
        parse_mode='HTML'
    )
    return ASK_USERNAME

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for phone number after receiving username"""
    context.user_data['username'] = update.message.text
    await update.message.reply_text(
        '📞 <b>Please enter your phone number:</b>',
        parse_mode='HTML'
    )
    return ASK_PHONE

async def ask_txid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show payment QR and ask for transaction ID"""
    context.user_data['phone'] = update.message.text

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton('✅ I Have Paid', callback_data='paid')],
        [InlineKeyboardButton('❌ Cancel Order', callback_data='cancel')]
    ])

    await update.message.reply_photo(
        photo=QR_IMAGE,
        caption="💳 <b>Payment Instructions:</b>\n\n"
                "1. Scan the QR code above\n"
                "2. Complete the payment via PhonePe or GooglePay\n"
                "3. Click '✅ I Have Paid' below when done\n\n"
                "<i>Note: Please keep your transaction ID ready.</i>",
        reply_markup=btn,
        parse_mode='HTML'
    )
    return SELECT_OFFER_STATE

async def paid_or_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle payment confirmation or cancellation"""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        await query.message.reply_text('❌ <b>Order canceled.</b>', parse_mode='HTML')
        return ConversationHandler.END
    elif query.data == 'paid':
        await query.message.reply_text(
            '🔢 <b>Please send your Transaction ID:</b>',
            parse_mode='HTML'
        )
        return ASK_TXID
    return SELECT_OFFER_STATE

async def save_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save the order to database"""
    user_id = update.effective_user.id
    username = context.user_data['username']
    phone = context.user_data['phone']
    offer = context.user_data['offer']
    txid = update.message.text

    with sqlite3.connect(DB) as db:
        db.execute(
            'INSERT INTO orders (user_id, username, phone, offer, txid) VALUES (?, ?, ?, ?, ?)',
            (user_id, username, phone, offer, txid)
        )
        db.commit()

    await update.message.reply_text(
        '🎉 <b>Thank you for your order!</b>\n\n'
        '✅ <b>Payment confirmed!</b>\n'
        'Your order is now being processed.\n\n'
        '📞 If you have any queries, contact us at <b>@Favas_786</b> or call <b>+917639724028</b>.\n'
        'You will be notified once it\'s completed.',
        parse_mode='HTML'
    )
    return ConversationHandler.END

async def vieworders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View all pending orders with copy-friendly formatting"""
    with sqlite3.connect(DB) as db:
        orders = db.execute('''
            SELECT id, user_id, username, phone, offer, txid, timestamp
            FROM orders
            WHERE status="pending"
            ORDER BY timestamp DESC
        ''').fetchall()

    if not orders:
        await update.message.reply_text('📭 <b>No pending orders.</b>', parse_mode='HTML')
        return

    for order in orders:
        oid, user_id, username, phone, offer, txid, timestamp = order

        # Format order details for easy copying
        order_details = (
            "══════════════════════════\n"
            f"📦 <b>Order #</b>{oid}\n"
            f"🆔 <b>User ID:</b> {user_id}\n"
            f"👤 <b>Username:</b> @{username}\n"
            f"📞 <b>Phone:</b> {phone}\n"
            f"🎁 <b>Offer:</b> {offer}\n"
            f"💳 <b>Transaction ID:</b> {txid}\n"
            f"⏰ <b>Date:</b> {timestamp}\n"
            "══════════════════════════"
        )

        # Create buttons
        keyboard = [
            [InlineKeyboardButton('✅ Mark as Completed', callback_data=f'finish:{oid}')],
            [InlineKeyboardButton('📋 Copy Order Details', callback_data=f'copy:{oid}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            order_details,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

async def finish_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mark an order as completed"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith('copy:'):
        # Handle copy order details request
        oid = query.data.split(':')[1]
        with sqlite3.connect(DB) as db:
            order = db.execute('''
                SELECT user_id, username, phone, offer, txid, timestamp
                FROM orders WHERE id=?
            ''', (oid,)).fetchone()

        if order:
            user_id, username, phone, offer, txid, timestamp = order
            copy_text = (
                f"Order #{oid}\n"
                f"User ID: {user_id}\n"
                f"Username: @{username}\n"
                f"Phone: {phone}\n"
                f"Offer: {offer}\n"
                f"Transaction ID: {txid}\n"
                f"Date: {timestamp}"
            )
            await query.message.reply_text(
                f"📋 <b>Order details (copy below):</b>\n\n"
                f"<code>{copy_text}</code>",
                parse_mode='HTML'
            )
        return

    # Handle order completion
    oid = query.data.split(':')[1]
    with sqlite3.connect(DB) as db:
        user_id = db.execute('SELECT user_id FROM orders WHERE id=?', (oid,)).fetchone()

        if user_id:
            try:
                # Notify user
                await context.bot.send_message(
                    chat_id=user_id[0],
                    text='🎉 <b>Your order has been completed!</b>',
                    parse_mode='HTML'
                )

                # Update database
                db.execute('UPDATE orders SET status="done" WHERE id=?', (oid,))
                db.commit()

                await query.edit_message_text(
                    f'✅ <b>Order #{oid} marked as completed!</b>',
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Error: {e}")
                await query.edit_message_text(
                    '⚠️ <b>Error processing order. User might have blocked the bot.</b>',
                    parse_mode='HTML'
                )
        else:
            await query.edit_message_text('❌ <b>Order not found.</b>', parse_mode='HTML')

# ===================== MAIN APP SETUP =====================

def main() -> None:
    """Start the bot"""
    init_db()
    app = Application.builder().token(TOKEN).build()

    # User: Order placement conversation handler
    order_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_TYPE_STATE: [CallbackQueryHandler(select_type, pattern='^category:')],
            SELECT_OFFER_STATE: [
                CallbackQueryHandler(select_offer, pattern='^select:'),
                CallbackQueryHandler(paid_or_cancel, pattern='^(paid|cancel)$')
            ],
            ASK_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_txid)],
            ASK_TXID: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_order)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Add all handlers
    app.add_handler(order_handler)
    app.add_handler(CommandHandler('vieworders', vieworders))
    app.add_handler(CallbackQueryHandler(finish_order, pattern='^(finish|copy):'))

    # Start the bot
    print('🤖 Bot is running...')
    app.run_polling()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel any ongoing conversation"""
    await update.message.reply_text('❌ <b>Operation canceled.</b>', parse_mode='HTML')
    return ConversationHandler.END

if __name__ == '__main__':
    main()

import json
from groupy.client import Client
from groupy.api.bots import Bot
from groupy.api.groups import Group
from groupy.api.attachments import Attachment
import requests
import datetime
from apscheduler.schedulers.background import BlockingScheduler
import sys
from sheets import Sheets
from configuration import Configuration
from metadata import Metadata
import os
import atexit
from loguru import logger
from functools import lru_cache
from gpt import GPT
from models.Trade import Trade, TradeConsenter


from sleeper.model import Player
from insults.InsultManager import  InsultManager

from database.database import Database
from models.Sidebet import Sidebet
import sleeper_wrapper


def get_bot_by_bot_name(name, group_id):
    client = Client.from_token(all_configs['GROUPME_API_TOKEN'])
    bots = client.bots.list()
    for bot in bots:
        if bot.bot_id == all_configs['GROUPME_BOT_ID']:
            return bot


@lru_cache
def get_current_group():
    client = Client.from_token(all_configs['GROUPME_API_TOKEN'])
    groups = client.groups.list_all()

    for group in groups:
        if group.data["id"] == all_configs['GROUPME_GROUP_ID']:
            return group


def get_latest_messages():
    new_message = False
    group: Group = get_current_group()
    try:
        latest_messages = group.messages.list_after(metadata.get_metadata_field('LAST_CHECKED_MSG_ID'))
    except Exception as ex:
        logger.error("Exception: " + str(ex))
        return
    if len(latest_messages.items) > 0:
        if latest_messages[-1].data['id'] != metadata.get_metadata_field('LAST_CHECKED_MSG_ID'):
            new_message = True
            metadata.write_metadata_field('LAST_CHECKED_MSG_ID', latest_messages[-1].data['id'])
    return new_message, latest_messages


def get_latest_trade():
    trades = sleeper_wrapper.get_trades(all_configs['SLEEPER_LEAGUE_ID'], all_configs['PLAYER_FILE'])
    new_trades = []
    new_trade = False
    if trades[-1].last_updated != metadata.get_metadata_field('LAST_CHECKED_TRADE_TIMESTAMP'):
        new_trade = True
        new_trades = list(filter(
            lambda transaction: transaction.last_updated > metadata.get_metadata_field('LAST_CHECKED_TRADE_TIMESTAMP'),
            trades))
        metadata.write_metadata_field('LAST_CHECKED_TRADE_TIMESTAMP', trades[-1].last_updated)
    if os.environ.get('DEBUG') == 'True':
        return True, [trades[-1]]
    return new_trade, new_trades


def write_message(message, attachments=None, data=None):
    if len(message) > 1000:
        logger.error(f"Message greater than 1000 characters. Length: {len(message)}")
        # message = "Response was unable to be posted. Reason: message > 1000 characters."
        messages = message.split('.')
        length = 0
        msg_to_send = ""
        for message in messages:
            message += '. '
            if length < 500:
                msg_to_send += message
                length += len(message)
            else:
                BOT.post(msg_to_send, attachments)
                length = 0
                msg_to_send = ""
        return
    if attachments is None:
        attachments = []
    BOT.post(message, attachments)


def create_trade_poll(trade: Trade):
    url = all_configs['GROUPME_API_URL'] + 'poll/' + all_configs['GROUPME_GROUP_ID'] + "?token=" + all_configs['GROUPME_API_TOKEN']

    current_timestamp = datetime.datetime.now().timestamp()
    tomorrow = round(current_timestamp + 82000)

    num_map = {
        1: '1st',
        2: '2nd',
        3: '3rd'
    }

    options = []
    for owner_id, received in trade.consenters.items():
        option = all_configs['SLEEPER_ID_TO_OWNER_NAME'][owner_id] + ' receives: '
        for player in received.players:
            option += f'{player.first_name} {player.last_name}, '
        for pick in received.draft_picks:
            option += f'{pick.season} {num_map[pick.round]}, '
        option += f'{received.faab} faab. \n'
        options.append({"title": option})

    options.append({"title": "No one..it actually seems fair."})

    data = {
        "subject": "Instant reaction: Who got fleeced?",
        "options": options,
        "expiration": tomorrow,
        "type": "single",
        "visibility": "public"
    }

    r = requests.post(url, data=json.dumps(data))
    if r.status_code != 201:
        logger.error("Error posting poll: " + r.text)


def add_all_to_message(msg_length, attachments: list[Attachment]):
    if len(attachments) == 0:
        attachments.append(Attachment('mentions'))

    attachments[0].data['loci'] = []
    attachments[0].data['user_ids'] = []

    i = 0
    for member in get_current_group().members:
        attachments[0].data['loci'].append([0, msg_length])
        attachments[0].data['user_ids'].append(member.user_id)
        i += len(member.nickname) + 2
    return attachments


def process_sidebet(message):
    elements = message.split(',')
    if len(elements) != 4:
        write_message(
            "Invalid sidebet format! It must be in the format of '+sidebet Owner 1, Owner 2, consequence, details'")
    else:
        sidebet = Sidebet(elements[0].strip(), elements[1].strip(), elements[2].strip(), elements[3].strip())
        write_message("Sidebet has been recorded as: " + str(sidebet))
        sheet.add_sidebet(sidebet)
        if USING_DATABASE:
            with Database(all_configs['SLEEPER_LEAGUE_ID']) as db:
                db.execute(sidebet)


def remove_keyword(message, keyword):
    return message.split(keyword, 1)[1].strip()


def format_insult(insult, attachments: list[Attachment]):
    members = get_current_group().members
    nickname = ""
    for member in members:
        if member.user_id == attachments[0].data['user_ids'][0]:
            nickname = member.nickname
    insult = f'@{nickname} - {insult}'
    attachments[0].data['loci'][0][1] = len(insult)
    return insult, attachments


def gpt_call(message):
    chat_completion = gpt.chat_completion(message)
    base = "[GPT]: "
    return f"{base} {chat_completion}"


def message_switch(data):
    message = data.text
    user = data.name
    attachments = data.attachments

    if message.startswith("@all"):
        msg = remove_keyword(message, "@all")
        attachments = add_all_to_message(len(msg), attachments)
        write_message(msg, attachments)
        logger.debug("Mentioned all.")
    elif message.startswith("+repeat"):
        msg = '{}, you sent "{}".'.format(user, remove_keyword(message, "repeat"))
        if DEBUG:
            msg = remove_keyword(message, "repeat")
            attachments = add_all_to_message(len(remove_keyword(message, "repeat")), attachments)
        write_message(msg, attachments)
    elif message.startswith("+insult"):
        insult = insult_manager.get_insult_as_text(data.data['sender_id'], attachments[0].user_ids[0])
        attachments = data.attachments
        if len(attachments) == 1:
            insult, attachments = format_insult(insult, attachments)
        write_message(insult, attachments)
    elif message.startswith("+sidebet"):
        process_sidebet(remove_keyword(message, "sidebet"))
    elif message.startswith("+gpt"):
        write_message(gpt_call(remove_keyword(message, "gpt")), attachments)
    elif message.startswith("+help"):
        msg = "Here is the help documentation for The Dude:\n\n" \
              "'+repeat {message}' - repeat your message\n\n" \
              "'+insult {mention someone}' - insult someone\n\n" \
              "'+sidebet {Owner 1}, {Owner 2}, {consequence}, {details} - log a sidebet to the google sheet'\n\n" \
              "'+gpt {prompt} - Get a response from GPT. Expect a delay in response.\n\n" \
              "'@all {message}' - repeat the message, mention everyone\n\n" \
              "'+help' - show this help message"
        write_message(msg, attachments)


def check_messages():
    new_message, messages = get_latest_messages()
    for message in messages:
        if new_message and message.text is not None:
            logger.debug("[" + str(message.created_at) + "] [" + message.name + "]: " + message.text)
            message_switch(message)


def check_trades():
    logger.trace('Checking trades...')
    new_trade, trades = get_latest_trade()
    if new_trade:
        write_message("A new trade has occurred!")
        for trade in trades:
            create_trade_poll(trade)
            logger.debug(f'New trade: {trade}')


def exit_handler():
    write_message(f"{all_configs['GROUPME_BOT_NAME']} has been shutdown. Messages will no longer be delivered to him.")
    scheduler.shutdown()


def setup_db():
    with Database(all_configs['SLEEPER_LEAGUE_ID']) as db:
        db.create_sidebets_table()
        USING_DATABASE = True


def setup_logger():
    log_level = "TRACE" if DEBUG else "DEBUG"
    logger.remove()
    logger.add(sys.stderr, level=log_level)
    logger.add("app.log", level=log_level)


if __name__ == '__main__':

    DEBUG = bool(os.environ.get('DEBUG'))
    USING_DATABASE = False

    setup_logger()

    metadata = Metadata()
    all_configs = Configuration().get_all_configs()
    sheet = Sheets(all_configs['GOOGLE_SHEET_ID'], all_configs['WORKSHEET_NAME'])

    # setup_db()
    atexit.register(exit_handler)

    gpt = GPT()
    BOT: Bot = get_bot_by_bot_name(all_configs['GROUPME_BOT_NAME'], all_configs['GROUPME_GROUP_ID'])
    league = sleeper_wrapper.get_league(all_configs['SLEEPER_LEAGUE_ID'])
    insult_manager = InsultManager()

    # transactions = sleeper_wrapper.get_trades(all_configs['SLEEPER_LEAGUE_ID'])
    write_message(f"{all_configs['GROUPME_BOT_NAME']} is alive. Expect delays when making GPT calls.")
    check_messages()
    check_trades()

    scheduler = BlockingScheduler()
    scheduler.add_job(check_messages, 'interval', seconds=2, max_instances=3)
    scheduler.add_job(check_trades, 'interval', seconds=30)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)

    # See PyCharm help at https://www.jetbrains.com/help/pycharm/

import json
import groupy.api.groups
from groupy.client import Client
import requests
import datetime
from apscheduler.schedulers.background import BlockingScheduler
import sys
import keyboard
from sheets import Sheets
from configuration import Configuration
from metadata import Metadata
import os
import atexit

from sleeper.model import Player

from database.database import Database
from models.Sidebet import Sidebet
import sleeper_wrapper

USER_ID_TO_PERSON_MAP = {
    '76465061719588864': 'Drew Davis',
    '81262579812810752': 'Justin Alt',
    '94591622507282432': 'Victor Markus',
    '333314910077321216': 'Sam Calmes',
    '458362349540077568': 'Andrew Keal',
    '458362357068853248': 'James Stecker',
    '458362753975840768': 'Jake Folz',
    '458428894018531328': 'Joe Keal',
    '531163651048280064': 'Elliot Barquest',
    '604372706426691584': 'Mike Letizia'
}


def pprint(str):
    print(json.dumps(str, indent=2))


def get_bot_by_bot_name(name, group_id):
    global BOT
    url = all_configs['GROUPME_API_URL'] + "bots?token=" + all_configs['GROUPME_API_TOKEN']
    resp_j = requests.get(url).json()
    for bot in resp_j['response']:
        if bot['name'] == name and bot['group_id'] == group_id:
            BOT = bot


def get_group_members():
    group_id = BOT['group_id']
    url = all_configs['GROUPME_API_URL'] + "groups/" + group_id + "?token=" + all_configs['GROUPME_API_TOKEN']
    members = requests.get(url).json()['response']['members']
    member_id_list = list()
    for member in members:
        mem = {
            'user_id': member['user_id'],
            'length': len(member['nickname']),
            'nick': member['nickname']
        }
        member_id_list.append(mem)
    return member_id_list



def get_latest_messages():
    url = all_configs['GROUPME_API_URL'] + "groups/" + BOT['group_id'] + "/messages?token=" + all_configs['GROUPME_API_TOKEN'] + "&after_id=" + metadata.get_metadata_field('LAST_CHECKED_MSG_ID')
    newMessage = False
    base_model = requests.get(url).json()
    print(base_model)
    latest_messages = base_model['response']['messages']
    if len(latest_messages) > 0:
        if latest_messages[-1]['id'] != metadata.get_metadata_field('LAST_CHECKED_MSG_ID'):
            newMessage = True
            metadata.write_metadata_field('LAST_CHECKED_MSG_ID', latest_messages[-1]['id'])
            # write_last_checked_msg_id(LAST_CHECKED_MSG_ID, latest_messages[-1]['id'])
    return newMessage, latest_messages


def get_latest_trade():
    transactions = sleeper_wrapper.get_trades(all_configs['SLEEPER_LEAGUE_ID'], all_configs['PLAYER_FILE'])
    new_trades =[]
    new_trade = False
    if transactions[-1].last_updated != metadata.get_metadata_field('LAST_CHECKED_TRADE_TIMESTAMP'):
        new_trade = True
        new_trades = list(filter(lambda transaction: transaction.last_updated > metadata.get_metadata_field('LAST_CHECKED_TRADE_TIMESTAMP'), transactions))
        metadata.write_metadata_field('LAST_CHECKED_TRADE_TIMESTAMP', transactions[-1].last_updated)
    return new_trade, new_trades


def write_message(message, attachments=None, data=None):
    if attachments is None:
        attachments = []
    url = all_configs['GROUPME_API_URL'] + "/bots/post?token=" + all_configs['GROUPME_API_TOKEN']
    params = dict()
    datas = {
        'bot_id': BOT['bot_id'],
        'text': message,
        'attachments': attachments
    }
    if data is not None:
        datas['attachments']: data['attachments']
    params = json.dumps(datas).encode('utf8')
    resp_js = requests.post(url, data=params, headers={'content-type': 'application/json'})


def create_poll():

    url = 'https://api.groupme.com/v3/poll/' + metadata.get_metadata_field('GROUPME_GROUP_ID') + "?token=" + metadata.get_metadata_field('GROUPME_API_TOKEN')

    current_timestamp = datetime.datetime.now().timestamp()
    tomorrow = round(current_timestamp + 82000)
    print(tomorrow)
    data = {
        "subject": "Poll me?",
        "options": [
            {"title": "Yes"},
            {"title": "Absolutely"}
        ],
        "expiration": tomorrow,
        "type": "multi",
        "visibility": "public"
    }

    r = requests.post(url, data=json.dumps(data))
    write_message(r.text)
    print(r)


def get_insult():
    return requests.get("https://evilinsult.com/generate_insult.php?lang=en&type=json")

def add_all_to_message(msg_length):
    attachments = []
    attachments.append([])

    attachments[0] = {
        "type": "mentions",
        "loci": [],
        "user_ids": []
    }
    i = 0
    for member in GROUP.members:
        attachments[0]['loci'].append([0, msg_length])
        attachments[0]['user_ids'].append(member.user_id)
        i += len(member.nickname) + 2
    return attachments


def process_sidebet(message):
    elements = message.split(',')
    if len(elements) != 4:
        write_message("Invalid sidebet format! It must be in the format of '+sidebet Owner 1, Owner 2, consequence, details'")
    else:
        sidebet = Sidebet(elements[0].strip(), elements[1].strip(), elements[2].strip(), elements[3].strip())
        write_message("Sidebet has been recorded as: " + str(sidebet))
        sheet.add_sidebet(sidebet)
        if USING_DATABASE:
            with Database(all_configs['SLEEPER_LEAGUE_ID']) as db:
                db.execute(sidebet)


def remove_keyword(message, keyword):
    return message.split(keyword, 1)[1].strip()


def format_insult(insult, attachments):
    members = get_group_members()
    nickname = ""
    for member in members:
        if member['user_id'] == attachments[0]['user_ids'][0]:
            nickname = member['nick']
    insult = f'@{nickname} - {insult}'
    attachments[0]['loci'][0][1] = len(insult)
    return insult, attachments


def message_switch(data):
    message = data['text']
    user = data['name']
    attachments = {}

    if message.startswith("@all"):
        print(GROUP.members)
        msg = remove_keyword(message, "@all")
        attachments = add_all_to_message(len(msg))
        write_message(msg, attachments)
        print("Mentioned all.")
    elif message.startswith("poll"):
        create_poll()
    elif message.startswith("+repeat"):
        msg = '{}, you sent "{}".'.format(user, remove_keyword(message, "repeat"))
        if DEBUG:
            msg = remove_keyword(message, "repeat")
            attachments = add_all_to_message(len(remove_keyword(message, "repeat")))
        write_message(msg, attachments)
    elif message.startswith("+insult"):
        insult = get_insult().json()['insult']
        attachments = data['attachments']
        if len(attachments) == 1:
            insult, attachments = format_insult(insult, attachments)
        write_message(insult, attachments)
    elif message.startswith("+sidebet"):
        process_sidebet(remove_keyword(message, "sidebet"))
    elif message.startswith("+help"):
        msg = "Here is the help documentation for The Dude:\n\n" \
              "'+repeat {message}' - repeat your message\n\n" \
              "'+insult {mention someone}' - insult someone\n\n" \
              "'+sidebet Owner 1, Owner 2, consequence, details'\n\n" \
              "'@all {message}' - repeat the message, mention everyone\n\n" \
              "'+help' - show this help message"
        write_message(msg, attachments)


def check_messages():
    new_message, messages = get_latest_messages()
    for message in messages:
        if new_message and message['text'] is not None:
            print("[" + str(datetime.datetime.fromtimestamp(message['created_at'])) + "] [" + message['name'] + "]: " + message['text'])
            message_switch(message)


def check_trades():
    print('Checking trades...')
    newTrade, trades = get_latest_trade()
    players: dict[str, Player] = sleeper_wrapper.get_players(all_configs['PLAYER_FILE'])
    if newTrade:
        write_message("A new trade has occurred!")
        for trade in trades:
            cnt = 0
            str = ''
            for owner_id, received in trade.consenters.items():
                if cnt == 0:
                    str += USER_ID_TO_PERSON_MAP[owner_id] + ' has traded with '
                    cnt += 1
                else:
                    str += USER_ID_TO_PERSON_MAP[owner_id] + '!'
            write_message(str)
            print(trade)
    else:
        print('No new trades.')


def check_quit():
    isStopped = False
    # This is here to simulate application activity (which keeps the main thread alive).
    if keyboard.is_pressed('Esc'):
        print("Esc pressed")
        if not isStopped:
            write_message("The Dude has been shutdown. Messages will no longer be delivered to him.")
            isStopped = True
            scheduler.shutdown()
            print('Exiting on Esc...')
            sys.exit(0)


def exit_handler():
    write_message(f"{all_configs['GROUPME_BOT_NAME']} has been shutdown. Messages will no longer be delivered to him.")
    scheduler.shutdown()


def setup_db():
    with Database(all_configs['SLEEPER_LEAGUE_ID']) as db:
        db.create_sidebets_table()
        USING_DATABASE = True



if __name__ == '__main__':
    CLIENT = ''
    GROUP: groupy.api.groups.Group
    # all_configs = {}
    BOT = None
    DEBUG = bool(os.environ.get('DEBUG'))
    USING_DATABASE = False

    metadata = Metadata()
    all_configs = Configuration().get_all_configs()
    sheet = Sheets(all_configs['GOOGLE_SHEET_ID'], all_configs['WORKSHEET_NAME'])

    # setup_db()
    atexit.register(exit_handler)
    CLIENT = Client.from_token(all_configs['GROUPME_API_TOKEN'])
    groups = CLIENT.groups.list_all()
    for group in groups:
        if group.data["id"] == all_configs['GROUPME_GROUP_ID']:
            GROUP = group
            break

    get_bot_by_bot_name(all_configs['GROUPME_BOT_NAME'], all_configs['GROUPME_GROUP_ID'])
    league = sleeper_wrapper.get_league(all_configs['SLEEPER_LEAGUE_ID'])

    # transactions = sleeper_wrapper.get_trades(all_configs['SLEEPER_LEAGUE_ID'])
    write_message(f"{all_configs['GROUPME_BOT_NAME']} is alive.")
    check_messages()
    check_trades()

    scheduler = BlockingScheduler()
    scheduler.add_job(check_messages, 'interval', seconds=2)
    scheduler.add_job(check_trades, 'interval', seconds=30)

    # HOLD THE ESCAPE KEY TO EXIT THIS BOT GRACEFULLY
    # scheduler.add_job(check_quit, 'interval', seconds=2)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)


    # See PyCharm help at https://www.jetbrains.com/help/pycharm/




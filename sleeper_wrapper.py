from functools import lru_cache
import time
import pickle
import os
from sleeper.api import LeagueAPIClient, PlayerAPIClient
from sleeper.enum import Sport, TransactionType
from sleeper.model import (
    League,
    Roster,
    User,
    Matchup,
    Player,
    PlayoffMatchup,
    Transaction,
    TradedPick,
    SportState,
)
from models.Trade import Trade
from models.TradeConsenter import TradeConsenter
from loguru import logger

DEBUG = True

CACHE = {}

@lru_cache
def get_league_users(league_id):
    start = time.time()
    # get all users in a particular league
    if 'league_users' in CACHE:
        return CACHE['league_users']

    league_users: list[User] = LeagueAPIClient.get_users_in_league(league_id=league_id)
    rosters = get_league_rosters(league_id)
    users = {}
    for user in league_users:
        users[user.user_id] = user.display_name

    CACHE['league_users'] = league_users
    end = time.time()
    logger.trace("Time taken to retrieve league users: " + str(round(end - start, 2)) + " seconds")
    return league_users


def get_owner_id_by_roster_id(league_id, roster_id):
    for roster in get_league_rosters(league_id):
        if roster.roster_id == roster_id:
            return roster.owner_id
    return None


def get_roster_by_owner_id(league_id, owner_id):
    for roster in get_league_rosters(league_id):
        if roster.owner_id == owner_id:
            return roster
    return None

@lru_cache
def get_league_rosters(league_id):
    if 'league_rosters' in CACHE:
        return CACHE['league_rosters']

    # # get all rosters in a particular league
    league_rosters: list[Roster] = LeagueAPIClient.get_rosters(league_id=league_id)
    CACHE['league_rosters'] = league_rosters
    return league_rosters


def get_sport_state():
    # # get the state of a particular sport
    nfl_state: SportState = LeagueAPIClient.get_sport_state(sport=Sport.NFL)
    return nfl_state

@lru_cache
def get_league(league_id):
    if 'league' in CACHE:
        return CACHE['league']

    # get a league by its ID
    league: League = LeagueAPIClient.get_league(league_id=league_id)
    CACHE['league'] = league
    return league


@lru_cache
def get_players(player_file):
    if os.path.isfile(player_file):
        with open(player_file, 'rb') as f:
            return pickle.load(f)
    else:
        players = PlayerAPIClient.get_all_players(sport=Sport.NFL)
        with open(player_file, 'wb') as f:
            pickle.dump(players, f)
        return players


def get_trades(league_id, player_file):
    players: dict[str, Player] = get_players(player_file)
    league_users: list[User] = get_league_users(league_id)
    nfl_state: SportState = get_sport_state()
    # get all transactions in a week for a particular league
    all_transactions: list[Transaction] = []
    for i in range(nfl_state.week):
        all_transactions.extend(LeagueAPIClient.get_transactions(league_id=league_id, week=i))

    trades = list(filter(lambda transaction: transaction.type == TransactionType.TRADE, all_transactions))
    usable_trades = []
    for trade in trades:
        test = {
            'consenters': {}
        }
        all_consenters: dict[str, TradeConsenter] = {}
        consenter_obj = None
        for consenter in trade.consenter_ids:
            draft_picks = list(filter(lambda draft_pick: draft_pick.owner_id == consenter, trade.draft_picks))
            trade_players = []
            for player_id, roster_id in trade.adds.items():
                if roster_id == consenter:
                    trade_players.append(players.get(player_id));

            faab_received = list(filter(lambda faab: faab.receiver == consenter, trade.waiver_budget))
            faab_sent = list(filter(lambda faab: faab.sender == consenter, trade.waiver_budget))

            total_faab = 0
            for entry in faab_received:
                total_faab += entry.amount
            for entry in faab_sent:
                total_faab -= entry.amount
            consenter_obj = TradeConsenter(draft_picks, trade_players, total_faab)
            all_consenters[get_owner_id_by_roster_id(league_id, consenter)] = consenter_obj
            # test['consenters'][get_owner_id_by_roster_id(league_id, consenter)] = consenter_obj
        curr_trade = Trade(all_consenters, trade.transaction_id, trade.status_updated)
        # test['transaction_id'] = trade.transaction_id
        # test['last_updated'] = trade.status_updated
        usable_trades.append(curr_trade)
    usable_trades.sort(key=lambda x: x.last_updated, reverse=False)
    return usable_trades




    # # get all leagues for a user by its ID in a particular year
    # user_leagues: list[League] = LeagueAPIClient.get_user_leagues_for_year(
    #     user_id="my_user_id", sport=Sport.NFL, year="2020"
    # )
    #
    # # get all rosters in a particular league
    # league_rosters: list[Roster] = LeagueAPIClient.get_rosters(league_id="my_league_id")
    #
    # # get all users in a particular league
    # league_users: list[User] = LeagueAPIClient.get_users_in_league(league_id="my_league_id")
    #
    # # get all matchups in a week for a particular league
    # week_1_matchups: list[Matchup] = LeagueAPIClient.get_matchups_for_week(
    #     league_id="my_league_id", week=1
    # )
    #
    # # get the winners bracket for a particular league
    # winners_bracket: list[PlayoffMatchup] = LeagueAPIClient.get_winners_bracket(
    #     league_id="my_league_id"
    # )
    #
    # # get the losers bracket for a particular league
    # losers_bracket: list[PlayoffMatchup] = LeagueAPIClient.get_losers_bracket(
    #     league_id="my_league_id"
    # )
    #
    # # get all traded picks for a particular league
    # traded_picks: list[TradedPick] = LeagueAPIClient.get_traded_picks(league_id="my_league_id")
    #
    # # get the state of a particular sport
    # nfl_state: SportState = LeagueAPIClient.get_sport_state(sport=Sport.NFL)
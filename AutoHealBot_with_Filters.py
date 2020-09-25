#!/usr/bin/env python3
'''Habitica Autoheal Script for Healer Class'''

from os import system, name, path
from sys import exit, argv
from time import sleep
import datetime
import json
import logging
import requests


FILTER = ['114-8']    # names in array are filtered out

def GetApiStatus():
    '''get Habitica API status'''
    msg = 'https://habitica.com/api/v3/status'
    apistatus = json.loads(requests.get(msg, headers=XCLIENTHEADER).content)
    try:
        logging.debug('*** API-Status: ' + str(apistatus['data']['status']))
        if apistatus['data']['status'] != 'up':
            return False
        return True
    except:
        return False
    return
    

def clear():
    '''clear console'''
    # for windows
    if name == 'nt':
        _ = system('cls')
    # for mac and linux(here, os.name is 'posix')
    else:
        _ = system('clear')


def GetapiToken(apitokenpath):
    '''reads apiToken from file apiToken.txt. Generate Token-File with "GetapiToken.py"" if needed'''
    with open(str(apitokenpath) + '/apiToken.txt', 'r') as f:  # open Token file
        if f.readable:
            token = f.read()
    return token


def CastHeal():
    '''cast heal on all party members'''
    # spell: heal all PARTY members
    spell = 'healAll'
    # cast spell command
    cast = 'https://habitica.com/api/v3/user/class/cast/' + spell
    castspell = requests.post(cast, headers=XCLIENTHEADER)
    return [castspell.ok, castspell.content]


def CastProtectiveAura():
    '''cast protectAura all party members'''
    # spell: protectAura
    spell = 'protectAura'
    # cast spell command
    cast = 'https://habitica.com/api/v3/user/class/cast/' + spell
    castspell = requests.post(cast, headers=XCLIENTHEADER)
    return [castspell.ok, castspell.content]


def PostResultsToChat(thph):
    '''Post healing results to Habitica party chat'''
    msg = {'message': 'MetHorns AutoHealBot healed a total of ' + str(thph) + ' HP!'}
    postlink = 'https://habitica.com/api/v3/groups/party/chat/'
    postmsg = requests.post(postlink, data=msg, headers=XCLIENTHEADER)
    logging.debug(postmsg)
    return postmsg.ok


def GetPartyMembers():
    '''party member request template'''
    pmrt = 'https://habitica.com/api/v3/groups/party/members'

    memberdata = json.loads(requests.get(pmrt, headers=XCLIENTHEADER).content)
    partymembers = []
    for i in memberdata['data']:
        if i['profile']['name'] not in FILTER:
            partymembers.append(i['id'])
    return partymembers


def GetPartyHp():
    '''Get Hp of every party member, greatest Hp-Difference(maxHP-HP) and player Mp'''
    # member request template
    mrt = 'https://habitica.com/api/v3/members/'
    names = []
    hp = [[], []]
    mp = [[], []]
    for i in range(len(PARTY)):
        try:
            player = json.loads(requests.get(mrt + PARTY[i], headers=XCLIENTHEADER).content)
            names.append(player['data']['auth']['local']['username'])
            logging.debug('*** Getting data of %s' % player['data']['auth']['local']['username'])
            hp[0].append(int(player['data']['stats']['hp']))
            hp[1].append(int(player['data']['stats']['maxHealth']))
            if player['data']['auth']['local']['username'] == 'MetHorn':
                mp[0].append(int(player['data']['stats']['mp']))
                mp[1].append(int(player['data']['stats']['maxMP']))
            sleep(0.5)
        except:
            pass

    clear()
    logging.debug('HP-Overview:\n')
    ghpd = int(hp[1][0] - hp[0][0])  # greatest hp difference (maxhp-hp)
    thpd = ghpd  # total hp difference
    for i in range(len(names)):
        logging.debug('%s: HP %i/%i' % (names[i], hp[0][i], hp[1][i]))
        if hp[1][i] - hp[0][i] > ghpd:
            ghpd = hp[1][i] - hp[0][i]
        thpd += int(hp[1][i] - hp[0][i])
    logging.debug('-----\nGreatest HP-Difference: %i' % ghpd)
    logging.debug('Total HP-Difference: %i' % thpd)
    logging.debug('My MP: %i/%i' % (mp[0][0], mp[1][0]))
    return ghpd, thpd, [mp[0][0], mp[1][0]]


if __name__ == '__main__':
    DEBUG_OUT = True
    WRITE_LOG = False
    POST_HP_HEALED = False
    if len(argv) > 1:  # if command line argument present
        temp = argv[1].replace('-', '')
        for i in temp:
            if str(i).lower() == 'h' or str(i).lower() == '?':
                print(
                    'Use the following parameters:\n\th ... show this help\n\td ... disable debug information in console\n\tl ... write log file\n\tp ... post healed HP in party chat')
                exit(0)
            if str(i).lower() == 'd':
                DEBUG_OUT = False
            if str(i).lower() == 'l':
                WRITE_LOG = True
            if str(i).lower() == 'p':
                POST_HP_HEALED = True

    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    # disable logging here
    if not DEBUG_OUT:
        logging.disable(logging.CRITICAL)

    # Get Script path
    SCRIPT_PATH = path.dirname(path.realpath(__file__))

    # Get apiToken
    APITOKEN = GetapiToken(SCRIPT_PATH)
    logging.debug('*** My API-Token: ' + APITOKEN)
    METHORNS_ID = '2df0b746-2950-4d06-87c0-11032f0e650e'
    # generate x-client‐header
    XCLIENTHEADER = {'x-client': METHORNS_ID + 'MetHornsAutoHealerScript', 'x-api-user': METHORNS_ID,
                     'x-api-key': APITOKEN}

    # Test if API is ok
    excode = -99
    if not GetApiStatus():
        if WRITE_LOG and excode != 0:
            with open(SCRIPT_PATH + '/AutoHealBot.log', 'a+') as f:
                logtime = datetime.datetime.now()
                if f.writable:
                    f.write(
                    str(logtime).split('.')[0] + ' THPH: 0' + ' ExitC: -10' + '\n')
        logging.debug('*** API down!')
        exit(-10)

    # automatically get party members
    PARTY = GetPartyMembers()
    logging.debug('Party Member Count: %i' % len(PARTY))

    # Window: max. and total health difference which is ok
    WHPOK = 4  # if < player hp loss of party -> cast heal
    WTHPOK = int(len(PARTY))  # if < total hp loss of party -> cast heal

    # Window: MP Limit
    WMPLIM = 25

    allgood = True
    ghpd, thpd, mp = GetPartyHp()
    
    # if mana full -> minimize heal windows
    if mp[0] >= mp[1]:
        WHPOK = 1
        WTHPOK = int(len(PARTY) / 2)
    
    thph = 0  # total HP healed
    caststatus = [False, 'Unknown Error']
    while ghpd > WHPOK or thpd > WTHPOK or (mp[0] >= mp[1] and thpd > 0):  # while hp is not ok
        if mp[0] < WMPLIM:  # if there's not enough mana
            allgood = False  # reset ok flag
            caststatus = [False, 'Not enough Mana']
            break
        caststatus = CastHeal()    

        if not caststatus[0]:
            allgood = False  # reset ok flag
            break
        sleep(30)  # wait for server updating
        temp = int(thpd)  # store total hp difference
        ghpd, thpd, mp = GetPartyHp()
        thph += int(temp - thpd)

    if allgood and thph == 0:
        logging.debug('-----\nNo healing needed!')
        caststatus[0] = True
        caststatus[1] = ''
        excode = 0
    elif allgood and thph != 0:
        logging.debug('-----\nParty healed for a total of %i HP!' % thph)
        if POST_HP_HEALED:
            PostResultsToChat(thph)
        excode = 1
    elif not bool(caststatus[0]):
        logging.debug('-----\nError:\n%s' % caststatus[1])
        if thph > 0:
            logging.debug('But still the party healed for a total of %i HP!' % thph)
            if POST_HP_HEALED:
                PostResultsToChat(thph)
        excode = -1
    else:
        logging.debug('-----\nUnknown Error!!!!!')
        if thph > 0:
            logging.debug('But still the party healed for a total of %i HP!' % thph)
            if POST_HP_HEALED:
                PostResultsToChat(thph)
        excode = -2

    # *** !!! for running in Pydroid -> ALLWAYS LOG !!!
    if WRITE_LOG and excode != 0:
        with open(SCRIPT_PATH + '/AutoHealBot.log', 'a+') as f:
            logtime = datetime.datetime.now()
            if f.writable:
                f.write(
                    str(logtime).split('.')[0] + ' THPH: ' + str(thph) + ' ExitC: ' + str(excode) + '\n')

    # if mp > max_mp -> cast Protective Aura
    while mp[0] > mp[1]:
        temp = CastProtectiveAura()
        if temp[0] == False:
            break
        ghpd, thpd, mp = GetPartyHp()

    exit(excode)

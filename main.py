"""
╔════════════════════════════════════════════════════════════╗
║  Author  : pygot                                           ║
║  GitHub  : https://github.com/pygot                        ║
╚════════════════════════════════════════════════════════════╝
"""

from secret import cookie
from logger import log_it
from random import choice
from json import dumps
from time import time

import requests
import asyncio
import pytchat

CONFIG = {
    'price_max': 5,
    'video_id': 'dQw4w9WgXcQ',
    'giveaway_threshold': 120,
    'max_wins_per_user': 3,
    'command_prefix': 'join'
}


def get_gamepass(username):
    """
    Fetches game pass information and user ID for a given username.

    This function retrieves the user ID of the provided username and fetches all
    associated game passes for the games created by the user. It filters the game passes
    based on the price range defined in the configuration and determines the maximum priced
    game pass. If a valid game pass is found, its additional product information is retrieved.
    If there are no valid game passes or in case of an error, `None` is returned for either
    or both outputs.

    :param username: The username whose game pass and user ID are to be retrieved.
    :type username: str

    :return: A tuple containing the game pass details and the user ID. The game pass
        details include its name, price, ID, and associated product ID. Returns (None, None)
        in case of errors or if no valid game pass is found.
    :rtype: tuple[dict | None, str | None]
    """
    try:
        user_id = requests.post(
            url='https://users.roproxy.com/v1/usernames/users',
            json={'usernames': [username], 'excludeBannedUsers': True}
        ).json()['data'][0]['id']
    except: return None, None

    games = requests.get(f'https://games.roproxy.com/v2/users/{user_id}/games?limit=50&sortOrder=Asc')
    games_data = games.json().get('data', [])

    gamepass = []

    for game in games_data:
        game_id = game.get('id')

        gamepasses = requests.get(f'https://games.roproxy.com/v1/games/{game_id}/game-passes?limit=100&sortOrder=Asc')
        gamepass_data = gamepasses.json().get('data', [])

        filtered_passes = [
            {'name': gp.get('name', 'Unnamed Pass'), 'price': gp.get('price'), 'id': gp.get('id')}
            for gp in gamepass_data
            if gp.get('price') is not None and 1 <= gp['price'] <= CONFIG['price_max']
        ]

        gamepass.extend(filtered_passes)

    if gamepass:
        gamepass = max(gamepass, key=lambda x: x['price'])
        gamepass['product_id'] = requests.get(f'https://economy.roproxy.com/v1/game-pass/{gamepass["id"]}/game-pass-product-info').json()['ProductId']
    else: gamepass = None

    return gamepass, user_id


def delete_buy(gamepass):
    """
    Deletes ownership of a given gamepass and attempts to purchase it again using a provided
    session. This function interacts with the Roblox API to revoke the ownership of the
    specified gamepass and re-purchase it using provided credentials and gamepass details.

    :param gamepass: List containing gamepass details. The first element should be a dictionary
        with keys `id`, `name`, `price`, and `product_id` containing the respective details of
        the gamepass. The second element should be the seller ID (integer or string).
    :type gamepass: list
    :return: None
    """
    session = requests.Session()
    session.cookies['.ROBLOSECURITY'] = cookie

    gamepass_id = gamepass[0]['id']
    headers = {
        'Origin': 'https://www.roblox.com',
        'Referer': f'https://www.roblox.com/game-pass/{gamepass_id}/{gamepass[0]["name"].strip()}',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'x-csrf-token': session.post(f'https://auth.roblox.com/v2/login').headers['X-CSRF-Token'],
    }

    session.post(f'https://apis.roblox.com/game-passes/v1/game-passes/{gamepass_id}:revokeownership', headers=headers)

    headers['Referer'] = 'https://www.roblox.com/'
    headers['Content-Type'] = 'application/json; charset=UTF-8'

    response = session.post(
        url=f'https://apis.roblox.com/game-passes/v1/game-passes/{gamepass[0]["product_id"]}/purchase',
        headers=headers,
        data=dumps({'expectedCurrency': 1, 'expectedPrice': gamepass[0]['price'], 'expectedSellerId': gamepass[1]})
    )

    if not response.json().get('purchased', False):
        print(response.json())


async def main():
    """
    Coordinates and manages a continuous giveaway process in a live chat platform. This is executed
    by monitoring chat messages for commands initiated by users, assessing their eligibility based
    on the predefined rules, and finally selecting, announcing, and processing a winner. The entire
    process repeats until manually stopped or interrupted.

    Sections include monitoring chat activity, validating participants, managing their eligibility,
    randomly selecting winners, and performing actions related to the giveaway.

    :raises KeyboardInterrupt: Raised when the process is interrupted manually.
    :raises Exception: Raised for any unexpected error during the execution.

    :return: None
    """
    try:
        chat = pytchat.create(video_id=CONFIG['video_id'])
        winners = {}

        while True:
            participants = []
            start_time = time()

            try:
                log_it('Starting the next giveaway...')

                while chat.is_alive() and time() - start_time < CONFIG['giveaway_threshold']:
                    for item in chat.get().sync_items():
                        message = str(item.message)
                        prefix = CONFIG['command_prefix']

                        if (message := message.lower().replace(' ', '')) and message.startswith(prefix):
                            username = message.replace(prefix, '').capitalize()

                            if username and winners.get(username, 0) <= CONFIG['max_wins_per_user']:

                                if any(p[2] == username for p in participants):
                                    log_it(f'User {username} is already in giveaway!')
                                    continue

                                try: gamepass, user_id = await asyncio.to_thread(get_gamepass, username)
                                except Exception as e:
                                    log_it(e, 2)
                                    continue

                                if gamepass:
                                    participants.append([gamepass, user_id, username])
                                    log_it(f'Successfully joined {username}!')
                            else:
                                log_it(f'User {username if username else "(Not Found)"} is not eligible for the giveaway.')
                                continue

                log_it('Selecting winner...')
                await asyncio.sleep(5)
                if participants:
                    winner = choice(list(participants))

                    log_it(f'Winner is... {winner[2]}!')

                    if winner[2] in winners: winners[winner[2]] += 1
                    else: winners[winner[2]] = 1

                    await asyncio.sleep(5)
                    log_it(f'Buying the {winner[0]["price"]}R$ gamepass...')
                    await asyncio.to_thread(delete_buy, [winner[0], winner[1]])
                    await asyncio.sleep(5)
                    log_it('Successfully bought the gamepass!')

                else: log_it('No one entered the giveaway..!?')

                await asyncio.sleep(2)
                log_it('Resetting the giveaway...')
                await asyncio.sleep(2)
            except Exception as e: log_it(e, 2)

    except KeyboardInterrupt: log_it('Closing...')
    except Exception as e: log_it(e, 2)


if __name__ == '__main__':
    asyncio.run(main())
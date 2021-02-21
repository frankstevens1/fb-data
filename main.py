import argparse
import logging
import traceback
import time
import json
import sys
import os

import schedule

from random import uniform

from selenium.common.exceptions import WebDriverException

def parse_arguments():
    """
    defines all command line arguments
    """
    parser = argparse.ArgumentParser(description='fb-data scrapes minute to minute football statistics.')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--games', action='store_true', 
                        help="list games with live stats available")
    action.add_argument('--check', action='store_true', 
                        help="list games scheduled for data collection")
    action.add_argument('--commit', action='store_true', 
                        help="commits selected games to data collection process")
    action.add_argument('--clear', action='store_true', 
                        help="clears selected games and scheduled games")
    action.add_argument('--cron', type=int, dest='match_id',
                        help="used by cron to run update for match_id X")
    arguments = parser.parse_args()
    return arguments

if __name__ == "__main__":
    # parse arguments
    args = parse_arguments()
    # change to project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    # open configuration settings
    with open('./config.json') as json_file:
        config = json.load(json_file)
    json_file.close()
    # create directories
    try:
        os.mkdir('./games')
    except FileExistsError:
        pass
    try:
        os.mkdir('./logs')
    except FileExistsError:
        pass
    # setup logging
    logging.basicConfig(handlers=[logging.FileHandler(
        filename=f'./logs/log.txt', encoding='utf-8', mode='a+')],
        format='%(asctime)s %(message)s',
        level=logging.INFO)
    # run requested function
    if args.games:
        for i in range(2):
            try:
                games_list = schedule.Update(config).games_list()
                game_data = games_list["GAME_DATA"]
                schedule.Schedule(config).prompt(game_data)
            except WebDriverException:
                logging.info(f'>> WebDriverException, retrying...')
                time.sleep(uniform(2,3))
                continue
            except Exception:
                logging.info(traceback.format_exc())
                sys.exit()
            else:
                break
        else:
            logging.info(f'>> games list update failed after 2 attempts')
            sys.exit()
    elif args.check:
        try:
            schedule.Schedule(config).check()
        except FileNotFoundError:
            print('''
        No games scheduled for data collection. 
        Run --games to view games available
            ''')
    elif args.commit:
        schedule.Schedule(config).commit()
    elif args.clear:
        schedule.Schedule(config).clear()
    elif args.match_id:
        schedule.cron_job(config, args.match_id)
        
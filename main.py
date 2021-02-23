import argparse
import logging
import json
import os
import psutil
import glob

import schedule
import parse

from pyvirtualdisplay import Display

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
    action.add_argument('--kill', action='store_true',
                        help="kill all application related processes")
    action.add_argument('--parse_all', action='store_true',
                        help="parses all json files in ./games/json")
    arguments = parser.parse_args()
    return arguments

def parse_all():
    """
    """
    pdir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(f"{pdir}/games/csv")
    files = []
    for file in glob.glob("*.csv"):
        files.append(file[:-4])
    os.chdir(f"{pdir}/games/json")
    unparsed = []
    for file in glob.glob("*.json"):
        if file[:-5] not in files:
            unparsed.append(file[:-5])
    for json_file in unparsed:
        parse.Parse(json_file).dataframe()

def kill_all(config):
    """
    kills all related processes
    """
    if config["LOCAL"] == 0:
        kill_processes = ['Xvfb', 'chromedriver', 'chrome']
        for proc in psutil.process_iter():
            if proc.name() in kill_processes:
                proc.kill()
    else:
        # windows kill process
        pass

if __name__ == "__main__":
    # parse arguments
    args = parse_arguments()
    display = Display(visible=0, size=(1024, 768))
    # change to project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    # open configuration settings
    with open('./config.json') as json_file:
        config = json.load(json_file)
    json_file.close()
    # create directories
    directories = ['./games', './games/csv', './games/json', './logs']
    for directory in directories:
        try:
            os.mkdir(directory)
        except FileExistsError:
            pass
    # setup logging
    logging.basicConfig(handlers=[logging.FileHandler(
        filename=f'./logs/log.txt', encoding='utf-8', mode='a+')],
        format='%(asctime)s %(message)s',
        level=logging.INFO)
    # run requested function
    if args.games:
        display.start()
        games_list = schedule.Update(config).games_list()
        display.stop()
        kill_all(config)
        game_data = games_list["GAME_DATA"]
        schedule.Schedule(config).prompt(game_data)
    elif args.check:
        try:
            schedule.Schedule(config).check()
        except FileNotFoundError:
            print('''
        No games scheduled for data collection. 
        Run --games to view games available
            ''')
    elif args.commit:
        display.start()
        schedule.Schedule(config).commit()
        display.stop()
        kill_all(config)
        parse_all()
    elif args.clear:
        schedule.Schedule(config).clear()
        kill_all(config)
    elif args.match_id:
        display.start()
        schedule.cron_job(config, args.match_id)
        display.stop()
        kill_all(config)
        parse_all()
    elif args.kill:
        kill_all(config)
        print('''
        All processes related to application killed.
            ''')
    elif args.parse_all:
        parse_all()
        print('''
        All json game data has been parsed to csv.
            ''')

        
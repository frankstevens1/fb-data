import argparse
import logging
import traceback
import inquirer
import time
import json
import sys
import os

import scrape

from pyvirtualdisplay import Display
from datetime import datetime, timedelta
from crontab import CronTab
from random import uniform
from os import path

from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException
from json.decoder import JSONDecodeError

class Update:
    """
    update games_list.json if required
    """
    def __init__(self, config):
        self.config = config

    def update(self):
        """
        """
        games_list = []
        for i in range(3):
            try:
                games_list = scrape.Games(config=self.config).get_game_list()
                with open(f'{self.config["PROJECT_PATH"]}games_list.json', 'w+') as outfile:
                    json.dump(games_list, outfile, indent=4)
                time.sleep(uniform(3,6))
            except TimeoutException:
                continue
            else:
                break
        else:
            logging.info('>> update failed after 3 attempts.')
            sys.exit()
        return games_list
    
    def games_list(self):
        """
        """
        cache = path.exists(f'{self.config["PROJECT_PATH"]}games_list.json')
        if cache:
            with open(f'{self.config["PROJECT_PATH"]}/games_list.json') as json_file: 
                games_list = json.load(json_file)
            json_file.close()
            last_checked = datetime.strptime(games_list["LAST_CHECKED"], "%d/%m/%Y %H:%M:%S")
            next_start = datetime.strptime(games_list["NEXT_START"], "%d/%m/%Y %H:%M:%S")
            last_start = datetime.strptime(games_list["NEXT_START"], "%d/%m/%Y %H:%M:%S")
            time_delta = next_start - last_checked
            if last_checked.day < datetime.utcnow().day:
                games_list = self.update()
            else:
                if datetime.utcnow() - last_checked  > time_delta and datetime.utcnow() < last_start:
                    games_list = self.update()
                else:
                    logging.info('>>> using cached games_list.json')
        else:
            games_list = self.update()
        return games_list

class Schedule:
    """
    groups all functionality to schedule games for data collection
    """
    def __init__(self, config):
        self.config = config

    def prompt(self, game_data):
        """
        prompts user to select games from games_list.json to schedule for data collection
        returns a nested dictionary:{
            ["SCHEDULE"]: {guid, match_id},
            ["REFRESH_RATE"]: refresh_rate,
            ["CRON_UPDATED]: 1/0 whether changes committed or not}
        """
        # format choices
        choices = []
        string_lengths = []
        user_selection = {"SCHEDULE": {}, "REFRESH_RATE": 'every 15 minutes', "CRON_UPDATED": 0}
        for game,data in game_data.items():
            string_lengths.append(len(data["LEAGUE"]))
        max_length = max(string_lengths)
        for game,data in game_data.items():
            value = (data["MATCH_ID"], game)
            start_time = data["START_TIME"][-8:-3]
            fill = r'%s-%ds' % ('%', max_length)
            league = fill % data["LEAGUE"]
            label = f'{start_time} - {league} - {data["HOME"]} vs {data["AWAY"]}'
            choices.append((label, value))
        # prompt selection
        questions = [
            inquirer.Checkbox(
            'games_schedule', 
            message='Select games',
            choices=choices),
            inquirer.List('refresh_rate',
                  message="Set desired refresh rate",
                  choices=['at 90+ minutes',
                           'every 15 minutes'])]
        responses = inquirer.prompt(questions)
        # user schedule to serializable format
        for match in responses['games_schedule']:
            match_id = match[0]
            label = match[1]
            user_selection["SCHEDULE"][label] = match_id
        user_selection["REFRESH_RATE"] = responses["refresh_rate"]
        with open(f'{self.config["PROJECT_PATH"]}user_selection.json', 'w+') as outfile:
            json.dump(user_selection, outfile, indent=4)
        outfile.close()
        logging.info(f'>> {self.config["PROJECT_PATH"]}user_selection.json updated')
        print('''
        Selected games have been staged for data collection.
        Run --commit to commit changes, or --games to change selection.
        ''')
        for match in responses['games_schedule']:
            print(f'         {match[1]}')
        print('')
        return user_selection
    
    def check(self):
        """
        prints user selection to console
        """
        with open(f'{self.config["PROJECT_PATH"]}user_selection.json') as json_file: 
            user_selection = json.load(json_file)
        json_file.close()
        with open(f'{self.config["PROJECT_PATH"]}games_list.json') as json_file: 
            game_data = json.load(json_file)["GAME_DATA"]
        json_file.close()
        string_lengths = []
        for game,data in game_data.items():
            string_lengths.append(len(data["LEAGUE"]))
        max_length = max(string_lengths)
        if user_selection["CRON_UPDATED"] == 1:
            print(f'''
        Data for the games below has been collected or scheduled for collection.
        Run --games to change selection.
            ''')
        else:
            print(f'''
        Games below have been selected for data collection.
        Run --commit to commit staged changes, or --games to change selection.
            ''')
        for guid in user_selection["SCHEDULE"]:
            start_time = game_data[guid]["START_TIME"][-8:-3]
            home = game_data[guid]["HOME"]
            away = game_data[guid]["AWAY"]
            fill = r'%s-%ds' % ('%', max_length)
            league = fill % game_data[guid]["LEAGUE"]
            label = f'{start_time} - {league} - {home} vs {away}'
            print(f'         {label}')
        print('')
    
    def ninety_plus(self, date_time):
        """
        take utc kick off time
        returns a tuple of (triggers, game_time)
        triggers are hour, minute combinations at which to trigger game data updates
        """
        game_time = date_time + timedelta(hours=1) # remove for utc environment
        ninety = game_time + timedelta(hours=1, minutes=15)
        triggers = [(ninety.hour, ninety.minute)]
        t = ninety
        for i in range(5):
            t = t + timedelta(minutes=15)
            triggers.append((t.hour, t.minute))
        return (triggers, game_time)

    def fifteen_minutes(self, date_time):
        """
        take utc kick off time
        returns a tuple of (triggers, game_time)
        triggers are hour, minute combinations at which to trigger game data updates
        """
        triggers = []
        game_time = date_time + timedelta(hours=1) # remove for utc environment
        hours = []
        for i in range(3):
            hours.append(game_time + timedelta(hours=i+1))
        hour_2 = hours[0].hour
        hour_3 = hours[1].hour
        hour_4 = hours[2].hour
        if game_time.minute != 00:
            d = 4
        else:
            d = 3
        hours_list = []
        for i in range(d+1):
            hours_list.append(game_time + timedelta(hours=i))
        for h in hours_list:
            if h.hour == game_time.hour:
                m = game_time.minute
                lm = 60
            elif h.hour == hour_2 or h.hour == hour_3:
                m = 00
                lm = 60
            elif h.hour == hour_4:
                m = 00
                lm = game_time.minute + 1
            else:
                break
            for i in range(m, lm, 15):
                triggers.append((h.hour,i))
        return (triggers, game_time)

    def update_crontab(self, matches_to_schedule):
        """
        writes commited schedule to crontab
        """
        with open(f'{self.config["PROJECT_PATH"]}user_selection.json') as json_file: 
            user_selection = json.load(json_file)
        json_file.close()
        game_times = set()
        if user_selection["REFRESH_RATE"] == 'every 15 minutes': # 15 minute setting
            for data in matches_to_schedule.values():
                schedule = self.fifteen_minutes(data["DATETIME"])
                triggers = schedule[0]
                game_times.add(schedule[1])
                data["TRIGGERS"] = triggers
        else: # 90+ setting
            for data in matches_to_schedule.values():
                schedule = self.ninety_plus(data["DATETIME"])
                triggers = schedule[0]
                game_times.add(schedule[1])
                data["TRIGGERS"] = triggers
        clear_cron = max(game_times) + timedelta(hours=3, minutes=1)
        my_cron = CronTab(user=self.config["USER_NAME"])
        job = my_cron.new(command=f'{self.config["PYTHON"]} {self.config["PROJECT_PATH"]}main.py --clear {self.config["CRON_LOGS"]}')
        job.set_comment('fb/cleanup')
        job.setall(clear_cron.minute, clear_cron.hour, clear_cron.day, clear_cron.month, None)
        my_cron.write()
        for comment,data in matches_to_schedule.items():
            i = 0
            for trigger in data["TRIGGERS"]:
                job = my_cron.new(command=data["COMMAND"])
                job.set_comment(comment + str(i))
                kick_off = data["DATETIME"]
                if trigger[0] < kick_off.hour:
                    day = kick_off + timedelta(days=1)
                else:
                    day = kick_off
                job.setall(trigger[1], trigger[0], day.day, kick_off.month, None)
                my_cron.write()
                i += 1
        print(f'''
        Upcoming matches will be scraped {user_selection["REFRESH_RATE"]} after kick-off.
        Data for matches past are saved in {self.config["PROJECT_PATH"]}games.
              ''')
        logging.info(f'>> crontab updated')

    def refresh_jobs(self):
        """
        removes undesired games from crontab
        returns latest schedule committed
        """
        with open(f'{self.config["PROJECT_PATH"]}user_selection.json') as json_file: 
            user_selection = json.load(json_file)
        json_file.close()
        games_scheduled = user_selection["SCHEDULE"]

        my_cron = CronTab(user=self.config["USER_NAME"])
        scheduled_jobs = set()
        for job in my_cron:
            if job.comment[:3] == 'fb/' and job.comment[3:] not in games_scheduled.keys():
                my_cron.remove(job)
            else:
                scheduled_jobs.add(job.comment)
        my_cron.write()
        now = datetime.utcnow()
        committed_schedule = {
            "SCHEDULE": {}
        }
        matches_past = []
        for guid,match_id in games_scheduled.items():
            if guid in scheduled_jobs:
                pass # already scheduled
            else:
                comment = 'fb/' + guid
                command = f'{self.config["PYTHON"]} {self.config["PROJECT_PATH"]}main.py --cron {match_id} {self.config["CRON_LOGS"]}'
                date_time = datetime(now.year, now.month, int(guid[6:8]), int(guid[:2]), int(guid[3:5]))
                if date_time + timedelta(minutes=90) < datetime.utcnow():
                    matches_past.append((guid.replace('/','').replace(':',''), match_id))
                else:
                    committed_schedule["SCHEDULE"][comment] = {
                        "COMMAND": command,
                        "DATETIME": date_time}
        committed_schedule["MATCHES_PAST"] = matches_past
        user_selection["CRON_UPDATED"] = 1
        with open(f'{self.config["PROJECT_PATH"]}user_selection.json', 'w+') as outfile:
            json.dump(user_selection, outfile, indent=4)
        outfile.close()
        return committed_schedule

    def clear(self):
        """
        """
        try:
            os.remove(f'{self.config["PROJECT_PATH"]}user_selection.json')
        except FileNotFoundError:
            pass
        my_cron = CronTab(user=self.config["USER_NAME"])
        for job in my_cron:
            if job.comment[:3] == 'fb/':
                my_cron.remove(job)
            else:
                pass
        my_cron.write()
        print(f'''
        Selection and schedule cleared.
               ''')

    def commit(self):
        """
        all matches selected are scheduled for data collection using crontab
        all matches selected that are 100 minutes past their kickoff time are updated
        """
        committed_schedule = self.refresh_jobs()
        matches_past = committed_schedule["MATCHES_PAST"]
        matches_to_schedule = committed_schedule["SCHEDULE"]
        for match in matches_past:
            scrape.Games(self.config).refresh_json(match)
        self.update_crontab(matches_to_schedule)
        logging.info('>> new schedule committed')


def cron_job(config, match_id):
    """
    used as the arugment when running updates from cron
    """
    with open(f'{config["PROJECT_PATH"]}user_selection.json') as json_file: 
        user_schedule = json.load(json_file)
    json_file.close()
    file_name = None
    for guid,m_id in user_schedule["SCHEDULE"].items():
        if m_id == match_id:
            file_name = guid.replace('/','').replace(':','')
        else:
            pass
    display = Display(visible=0, size=(1024, 768))
    display.start()
    scrape.Games(config).refresh_json((file_name,match_id))
    display.stop()
    logging.info(f'>> {file_name} updated')


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
    # set environment variables
    with open('/mnt/c/users/frank/projects/fb-data/config.json') as json_file: 
        config = json.load(json_file)
    json_file.close()
    # create directories
    try:
        os.mkdir(f'{config["PROJECT_PATH"]}games')
    except FileExistsError:
        pass
    try:
        os.mkdir(f'{config["PROJECT_PATH"]}logs')
    except FileExistsError:
        pass
    # setup logging
    logging.basicConfig(handlers=[logging.FileHandler(
        filename=f'{config["PROJECT_PATH"]}/logs/log.txt', encoding='utf-8', mode='a+')],
        format='%(asctime)s %(message)s',
        level=logging.INFO)
    if args.games:
        for i in range(2):
            try:
                display = Display(visible=0, size=(1024, 768))
                display.start()
                games_list = Update(config).games_list()
                display.stop()
                game_data = games_list["GAME_DATA"]
                Schedule(config).prompt(game_data)
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
            Schedule(config).check()
        except FileNotFoundError:
            print('''
        No games scheduled for data collection. 
        Run --games to view games available
            ''')
    elif args.commit:
        Schedule(config).commit()
    elif args.clear:
        Schedule(config).clear()
    elif args.match_id:
        for i in range(3):
            try:
                cron_job(config, args.match_id)
            except JSONDecodeError:
                logging.info(f'>> JSONDecodeError, retrying...')
                time.sleep(uniform(5,6))
                continue
            except Exception:
                logging.info(traceback.format_exc())
                sys.exit()
            else:
                break
        else:
            logging.info(f'>> {args.match_id} update failed after 3 attempts')
            sys.exit()

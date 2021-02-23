import scrape
from main import kill_all

import json
import os
import sys
import logging
import time
import inquirer
import traceback

from os import path
from random import uniform

from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException
from datetime import datetime, timedelta
from crontab import CronTab

class Update:
    """
    update games_list.json if required
    """
    def __init__(self, config):
        self.config = config

    def update(self):
        """
        updates the games_list.json cache
        """
        games_list = []
        for i in range(3):
            try:
                games_list = scrape.Games(config=self.config).get_game_list()
                with open('./games_list.json', 'w+') as outfile:
                    json.dump(games_list, outfile, indent=4)
                time.sleep(uniform(3,6))
            except TimeoutException:
                time.sleep(uniform(2,3))
                continue
            except WebDriverException:
                time.sleep(uniform(2,3))
                continue
            else:
                break
        else:
            logging.info(f'>> update failed after {i+1} attempts.')
        return games_list
    
    def games_list(self):
        """
        returns latest games_list
        """
        cache = path.exists('./games_list.json')
        if cache:
            with open(f'./games_list.json') as json_file: 
                games_list = json.load(json_file)
            json_file.close()
            last_checked = datetime.strptime(games_list["LAST_CHECKED"], "%d/%m/%Y %H:%M:%S")
            next_start = datetime.strptime(games_list["NEXT_START"], "%d/%m/%Y %H:%M:%S")
            last_start = datetime.strptime(games_list["LAST_START"], "%d/%m/%Y %H:%M:%S")
            time_delta = next_start - last_checked
            if last_checked.day < datetime.utcnow().day:
                games_list = self.update()
            elif datetime.utcnow() - last_checked  > time_delta and datetime.utcnow() < last_start:
                games_list = self.update()
            else:
                pass # don't update
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
        with open(f'./user_selection.json', 'w+') as outfile:
            json.dump(user_selection, outfile, indent=4)
        outfile.close()
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
        with open(f'./user_selection.json') as json_file: 
            user_selection = json.load(json_file)
        json_file.close()
        with open(f'./games_list.json') as json_file: 
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
    
    def ninety_plus(self, date_time, off_set):
        """
        take utc kick off time
        returns a tuple of (triggers, game_time)
        triggers are hour, minute combinations at which to trigger game data updates
        """
        print(date_time)
        if self.config["OFF_SET"] == 1:
            if self.config["LOCAL"] == 1:
                td = datetime.now() - datetime.utcnow()
                game_time = date_time + timedelta(hours=round(td.seconds / 3600, 1))
                gt_offset = game_time + timedelta(minutes=off_set)
            else:
                game_time = date_time
                gt_offset = game_time + timedelta(minutes=off_set)
        else:
            if self.config["LOCAL"] == 1:
                td = datetime.now() - datetime.utcnow()
                game_time = date_time + timedelta(hours=round(td.seconds / 3600, 1))
                gt_offset = game_time
            else:
                game_time = date_time
                gt_offset = game_time
        # create list of scrape times
        first = gt_offset + timedelta(minutes=120)
        last = first + timedelta(minutes=60)
        scrape_times = [first, last]
        # generate list of triggers
        triggers = []
        for scrape_time in scrape_times:
            triggers.append((scrape_time.hour, scrape_time.minute))
        return (triggers, game_time)

    def fifteen_minutes(self, date_time, off_set):
        """
        take utc kick off time and an offset in minutes
        returns a tuple of (triggers, game_time)
        triggers are hour, minute combinations at which to trigger game data updates
        """
        if self.config["OFF_SET"] == 1:
            if self.config["LOCAL"] == 1:
                td = datetime.now() - datetime.utcnow()
                game_time = date_time + timedelta(hours=round(td.seconds / 3600, 1))
                gt_offset = game_time + timedelta(minutes=off_set)
            else:
                game_time = date_time
                gt_offset = game_time + timedelta(minutes=off_set)
        else:
            if self.config["LOCAL"] == 1:
                td = datetime.now() - datetime.utcnow()
                game_time = date_time + timedelta(hours=round(td.seconds / 3600, 1))
                gt_offset = game_time
            else:
                game_time = date_time
                gt_offset = game_time
        # create list of scrape times
        first_scrape = gt_offset + timedelta(minutes=15)
        scrape_times = [first_scrape + timedelta(minutes=x) for x in range(0, 120, 15)]
        last_scrape = gt_offset + timedelta(minutes=180)
        scrape_times.append(last_scrape)
        # generate list of triggers
        triggers = []
        for scrape_time in scrape_times:
            triggers.append((scrape_time.hour, scrape_time.minute))
        return (triggers, game_time)

    def update_crontab(self, matches_to_schedule):
        """
        writes commited schedule to crontab
        """
        with open(f'./user_selection.json') as json_file: 
            user_selection = json.load(json_file)
        json_file.close()
        game_times = set()
        if user_selection["REFRESH_RATE"] == 'every 15 minutes': # 15 minute setting
            ko_hours = {}
            for data in matches_to_schedule.values():
                ko_hour = data["DATETIME"].hour
                if ko_hour in list(ko_hours.keys()):
                    schedule = self.fifteen_minutes(data["DATETIME"], ko_hours[ko_hour])
                    ko_hours[ko_hour] += 1
                else:
                    schedule = self.fifteen_minutes(data["DATETIME"], 0)
                    ko_hours[ko_hour] = 1
                if ko_hours[ko_hour] >= 14:
                    ko_hours[ko_hour] = 0
                triggers = schedule[0]
                game_times.add(schedule[1])
                data["TRIGGERS"] = triggers
        else: # 90+ setting (unused)
            ko_hours = {}
            for data in matches_to_schedule.values():
                ko_hour = data["DATETIME"].hour
                if ko_hour in list(ko_hours.keys()):
                    schedule = self.ninety_plus(data["DATETIME"], ko_hours[ko_hour])
                    ko_hours[ko_hour] += 1
                else:
                    schedule = self.ninety_plus(data["DATETIME"], 0)
                    ko_hours[ko_hour] = 1
                if ko_hours[ko_hour] >= 14:
                    ko_hours[ko_hour] = 0
                triggers = schedule[0]
                game_times.add(schedule[1])
                data["TRIGGERS"] = triggers
        clear_cron = max(game_times) + timedelta(hours=3, minutes=1)
        my_cron = CronTab(user=self.config["USER_NAME"])
        job = my_cron.new(command=f'{os.getcwd()}/.venv/bin/python3 {os.getcwd()}/main.py --clear >> {os.getcwd()}/logs/cronerrors.txt 2>> {os.getcwd()}/logs/cronlogs.txt')
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
        Data for matches past are saved in ./games.
              ''')

    def refresh_jobs(self):
        """
        removes undesired games from crontab
        returns latest schedule committed
        """
        with open(f'./user_selection.json') as json_file: 
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
                command = f'{os.getcwd()}/.venv/bin/python3 {os.getcwd()}/main.py --cron {match_id} >> {os.getcwd()}/logs/cronerrors.txt 2>> {os.getcwd()}/logs/cronlogs.txt'
                date_time = datetime(now.year, now.month, int(guid[6:8]), int(guid[:2]), int(guid[3:5]))
                if date_time + timedelta(minutes=90) < datetime.utcnow():
                    matches_past.append((guid.replace('/','').replace(':',''), match_id))
                else:
                    committed_schedule["SCHEDULE"][comment] = {
                        "COMMAND": command,
                        "DATETIME": date_time}
        committed_schedule["MATCHES_PAST"] = matches_past
        user_selection["CRON_UPDATED"] = 1
        with open(f'./user_selection.json', 'w+') as outfile:
            json.dump(user_selection, outfile, indent=4)
        outfile.close()
        return committed_schedule

    def clear(self):
        """
        """
        try:
            os.remove(f'./user_selection.json')
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
            for i in range(3):
                try:
                    scrape.Games(self.config).refresh_json(match)
                    updated = 'updated'
                except WebDriverException:
                    logging.info(f'>> WebDriverException, retrying...')
                    kill_all()
                    time.sleep(uniform(3,5))
                    continue
                except TimeoutException:
                    logging.info(f'>> TimeoutException, retrying...')
                    kill_all()
                    time.sleep(uniform(3,5))
                    continue
                except Exception:
                    logging.info(traceback.format_exc())
                    kill_all()
                    sys.exit()
                else:
                    break
            else:
                updated = f'update failed after {i+1} attempts'
            logging.info(f'>> {match[0]} {updated}')
        self.update_crontab(matches_to_schedule)

def cron_job(config, match_id):
    """
    used as the arugment when running updates from cron
    """
    with open(f'{os.getcwd()}/user_selection.json') as json_file: 
        user_schedule = json.load(json_file)
    json_file.close()
    file_name = None
    for guid,m_id in user_schedule["SCHEDULE"].items():
        if m_id == match_id:
            file_name = guid.replace('/','').replace(':','')
        else:
            pass
    for i in range(3):
        try:
            scrape.Games(config).refresh_json((file_name,match_id))
            updated = 'updated'
        except WebDriverException:
            logging.info(f'>> WebDriverException, retrying...')
            kill_all()
            time.sleep(uniform(3,5))
            continue
        except TimeoutException:
            logging.info(f'>> TimeoutException, retrying...')
            kill_all()
            time.sleep(uniform(3,5))
            continue
        except Exception:
            logging.info(traceback.format_exc())
            kill_all()
            sys.exit()
        else:
            break
    else:
        updated = f'update failed after {i+1} attempts'
    logging.info(f'>> {file_name} {updated}')
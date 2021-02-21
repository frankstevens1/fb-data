import logging
import re
import os
import json

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.common.exceptions import NoSuchElementException

from json.decoder import JSONDecodeError

from bs4 import BeautifulSoup
from datetime import datetime
from datetime import timedelta
from time import sleep
from random import uniform

class Games:
    """
    groups functionality to scrape game list and refresh game data
    """
    def __init__(self, config):
        self.config = config
        self.options = webdriver.ChromeOptions()
        self.options.add_experimental_option("excludeSwitches", ["enable-automation", "remote-debugging-port", "enable-logging"])
        self.options.add_experimental_option('useAutomationExtension', False)
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument(f"user-agent={self.config['USER_AGENT']}")
        self.options.add_argument('--no-sandbox')
        if self.config["LOCAL"] == 0:
            chromedriver = '/usr/bin/chromedriver'
        else:
            chromedriver = f'{os.getcwd()}/chromedriver/chromedriver.exe'
        self.driver = webdriver.Chrome(executable_path=chromedriver, options=self.options)
        self.url = self.config['URL_1']
        self.test = f'{os.getcwd()}/test/'
        
    def get_game_list(self):
        """
        returns a dictionary of all games listed on live scores page
        replaces last checked with datetime now 
        """
        # scrape match table html
        self.driver.get(self.url)
        sleep(uniform(2,3))
        ## start retry block
        for i in range(3):
            try:
                self.driver.find_element(By.XPATH, '//*[@id="view-sorted"]/dl[1]/dd[2]/a').click()
            except NoSuchElementException:
                sleep(uniform(1,3))
                continue
            except ElementClickInterceptedException:
                self.driver.find_element(By.XPATH, '//*[@id="qc-cmp2-ui"]/div[2]/div/button[2]').click()
                sleep(uniform(1,3))
                continue
            else:
                break
        else:
            raise Exception('Failed after 3 attempts.')
        ## end retry block
        match_table = self.driver.find_element(By.XPATH, '//*[@id="livescores"]/div/div')
        match_table_html = match_table.get_attribute('innerHTML')
        self.driver.quit()
        last_checked = datetime.utcnow()
        # parse html to json
        soup = BeautifulSoup(match_table_html, 'html.parser')
        ## json format
        game_data_dict = {
            "GAME_DATA": {
                # "GUID": {
                #"START_TIME": datetime string,
                #"HOME": string,
                #"AWAY": string,
                #"MATCH_ID": integer,
                #"LEAGUE": string,
            },
            "LAST_CHECKED": last_checked.strftime("%d/%m/%Y %H:%M:%S"),
            # "NEXT_START": timedelta string
            }
        ## append values
        upcoming_kickoffs = []
        t_minus = last_checked - timedelta(minutes=180)
        for row in soup.find_all("div"):            
            match_centre_link = row.find('a', class_="match-link rc live")
            match_preview_link = row.find('a', class_="match-link rc preview")
            match_report_link = row.find('a', class_="match-link rc match-report")
            if match_centre_link != None:
                link_text = match_centre_link['href']
                league = re.search(r'(?<=\/Live\/)[a-zA-Z\-]*', link_text).group()
            elif match_preview_link != None:
                link_text = match_preview_link['href']
                league = re.search(r'(?<=\/Preview\/)[a-zA-Z\-]*', link_text).group()
            elif match_report_link != None:
                link_text = match_report_link['href']
                league = re.search(r'(?<=\/MatchReport\/)[a-zA-Z\-]*', link_text).group()
            else:
                link_text = ''
                league = ''

            if link_text != '':
                match_id = int(re.search(r'\d{7}', link_text).group())
                try:
                    time = row.find("span", class_="time").string
                    start_time = datetime(datetime.utcnow().year, datetime.utcnow().month, datetime.utcnow().day, int(time[0:2]), int(time[-2:]))
                except AttributeError:
                    start_time = ''
                try:
                    teams = row.find_all("a", class_="team-link")
                    home = teams[0].string
                    away = teams[1].string
                except AttributeError:
                    home = ''
                    away = ''
                except IndexError:
                    home = ''
                    away = ''
            else:
                match_id = ''
                league = ''
                start_time = ''
                home = ''
                away = ''      
            if start_time != '' and start_time > t_minus and home != '' and away != '' and match_id != '':
                if start_time > datetime.utcnow():
                    upcoming_kickoffs.append(start_time)
                guid = f"{start_time.strftime('%H:%M-%d/%m/%Y')}-{home.rstrip().lstrip()}-{away.rstrip().lstrip()}".replace(' ', '_')
                game_data_dict["GAME_DATA"][guid] = {}
                game_data_dict["GAME_DATA"][guid]["START_TIME"] = start_time.strftime("%d/%m/%Y %H:%M:%S")
                game_data_dict["GAME_DATA"][guid]["HOME"] = home.rstrip().lstrip()
                game_data_dict["GAME_DATA"][guid]["AWAY"] = away.rstrip().lstrip()
                game_data_dict["GAME_DATA"][guid]["MATCH_ID"] = match_id
                game_data_dict["GAME_DATA"][guid]["LEAGUE"] = league.replace('-', ' ').rstrip().lstrip()
        next_start = min(upcoming_kickoffs)
        last_start = max(upcoming_kickoffs)
        game_data_dict['NEXT_START'] = next_start.strftime("%d/%m/%Y %H:%M:%S")
        game_data_dict['LAST_START'] = last_start.strftime("%d/%m/%Y %H:%M:%S")
        logging.info(f'>> {os.getcwd()}/games_list.json updated')
        if self.config["LOCAL"] == 1:
            os.system(f"taskkill.exe /F /IM chrome.exe >> /dev/null 2>&1")
        else:
            pass
        return game_data_dict

    def refresh_json(self, match: tuple):
        """
        takes a tuple of (guid, match_id)
        saves match data in /project_path/games/{guid}.json
        """
        url = self.config['URL_2'] % match[1]
        self.driver.get(url)
        content = self.driver.page_source
        content_string = content.replace('<html><head></head><body>', '')
        content_string = content_string.replace('</body></html>', '')
        file_name = match[0]
        try:
            json_data = json.loads(content_string)
            with open(f'{os.getcwd()}/games/{file_name}.json', 'w+') as json_file:
                json.dump(json_data, json_file, indent=4)
            json_file.close()
        except JSONDecodeError:
            logging.info(f'>> failed to refresh {match[0]}')
        self.driver.quit()
        if self.config["LOCAL"] == 1:
            os.system(f"taskkill.exe /F /IM chrome.exe >> /dev/null 2>&1")
        else:
            pass

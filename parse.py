import json
import pandas as pd
import os

columns = [
        'yellowCards_home',
        'redCards_home',
        'goals_home',
        'shotsTotal_home',
        'shotsOnTarget_home',
        'shotsBlocked_home',
        'cornersTotal_home',
        'foulsCommited_home',
        'tacklesTotal_home',
        'tackleSuccessful_home',
        'dribblesAttempted_home',
        'dribblesWon_home',
        'interceptions_home',
        'dispossessed_home',
        'aerialsTotal_home',
        'aerialsWon_home',
        'passesTotal_home',
        'passesAccurate_home',
        'possession_home',
        'touches_home',
        'clearances_home',
        'offsidesCaught_home',
        'yellowCards_away',
        'redCards_away',
        'goals_away',
        'shotsTotal_away',
        'shotsOnTarget_away',
        'shotsBlocked_away',
        'cornersTotal_away',
        'foulsCommited_away',
        'tacklesTotal_away',
        'tackleSuccessful_away',
        'dribblesAttempted_away',
        'dribblesWon_away',
        'interceptions_away',
        'dispossessed_away',
        'aerialsTotal_away',
        'aerialsWon_away',
        'passesTotal_away',
        'passesAccurate_away',
        'possession_away',
        'touches_away',
        'clearances_away',
        'offsidesCaught_away'
    ]

class Parse:
    def __init__(self, file_name):
        self.file_name = file_name
        self.columns = columns
        with open(f'{os.path.dirname(os.path.abspath(__file__))}/games/json/{self.file_name}.json') as json_file: 
            self.data = json.load(json_file)
        json_file.close()

    def minutes(self):
        """"""
        mins = set(self.data["home"]["stats"]["minutesWithStats"])
        away_mins = self.data["away"]["stats"]["minutesWithStats"]
        for min in away_mins:
            mins.add(min)
        return sorted(list(mins))

    def goals(self, side):
        """"""
        goals = {}
        for event in self.data[side]["incidentEvents"]:
            if event["type"]["displayName"] == 'Goal':
                goals[int(event["minute"])] = 1
        return goals

    def cards(self, side):
        """"""
        yellow_cards = {}
        red_cards = {}
        for event in self.data[side]["incidentEvents"]:
            if event["type"]["displayName"] == 'Card':
                if event["cardType"]["displayName"] == 'Yellow':
                    yellow_cards[int(event["minute"])] = 1
                else:
                    red_cards[int(event["minute"])] = 1
        return (yellow_cards, red_cards)

    def stats(self, side):
        """"""
        if side == "home":
            cols = self.columns[3:22]
        else:
            cols = self.columns[25:]
        stats = {}
        stats_json = self.data[side]["stats"]
        stats_json_int = {}
        for col,di in stats_json.items():
            try:
                stats_json_int[col] = {int(k):v for k,v in di.items()}
            except AttributeError:
                pass
        for col in cols:
            try:
                stats[col] = stats_json_int[col[:-5]]
            except KeyError:
                pass
        stats[f"goals_{side}"] = self.goals(side)
        stats[f"yellowCards_{side}"] = self.cards(side)[0]
        stats[f"redCards_{side}"] = self.cards(side)[1]
        return stats

    def dataframe(self):
        """"""
        mins = self.minutes()
        df = pd.DataFrame(0, index=mins, columns=self.columns)
        for side in ["home", "away"]:
            stats_side = self.stats(side)
            for col,di in stats_side.items():
                try:
                    df_update = pd.DataFrame.from_dict(di, orient='index')
                    df_update.columns = [col]
                    df.update(df_update)
                except ValueError:
                    pass
        df.to_csv(f"{os.path.dirname(os.path.abspath(__file__))}/games/csv/{self.file_name}.csv")
        return df
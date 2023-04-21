# Maintain experiment status
# When new experiment starts, set the status to active and start new variables with inputs
# Start a new csv file with the experiment name and current time
# When the experiment progresses, update the current count, and update the csv file
# When experiment ends, set experiment to inactive

import pandas as pd
from datetime import datetime

class Experiment:

    ACTIVE = False

    def __init__(self, tot_count = 20) -> None:
        self.tot_count = tot_count
        self.cur_count = 0
        self.exp_name = "debug"
        self.exp_id = "debug"
        self.csv_path = "saves/"+self.exp_id+".csv"
        self.create_df()

    def create_df(self):
        self.df = pd.DataFrame(columns=['text', 'score', 'time'])
        if self.ACTIVE: self.df.to_csv(self.csv_path, index=True)

    def update_empty(self, text = "Empty", score = "Empty"):
        # First append empty as soon as any update is to be made
        self.cur_count += 1
        new_row = {'text': text, 'score': score, 'time': self.get_time()}
        self.df = self.df.append(new_row, ignore_index=True)
        if self.ACTIVE: self.df.to_csv(self.csv_path, index=True)

    def update_last_row(self, text = "Empty", score = "Empty"):
        # Then replace the last row if successfully submitted the form
        self.df.iloc[-1, self.df.columns.get_loc('text')] = text
        self.df.iloc[-1, self.df.columns.get_loc('score')] = score
        self.df.iloc[-1, self.df.columns.get_loc('time')] = self.get_time()

        if self.ACTIVE: self.df.to_csv(self.csv_path, index=True)
    
    def get_status(self):
        if self.ACTIVE:
            return self.cur_count, self.tot_count, self.exp_id, self.get_df()
        else:
            return "exp inactive", "exp inactive", "exp inactive", self.get_df()
    
    def get_df(self):
        if self.ACTIVE:
            # Return active df
            return self.df.to_dict(orient='records')
        else:
            # Return inactive df
            inactive_df = pd.DataFrame({'text': "exp inactive", 'score': "exp inactive", 'time': "exp inactive"}, index=[0])
            return inactive_df.to_dict(orient='records')
    
    def get_time(self):
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def start(self, exp_name = "demo", total = 20):
        self.ACTIVE = True
        self.cur_count = 0
        self.tot_count = total
        self.exp_name = exp_name
        self.exp_id = self.exp_name+"_"+ self.get_time()
        self.csv_path = "saves/"+self.exp_id+".csv"
        self.create_df()
    
    def end(self):
        self.ACTIVE = False
        self.cur_count = 0
        self.tot_count = 20
        self.exp_name = "debug"
        self.exp_id = "debug"
        self.csv_path = "saves/"+self.exp_id+".csv"
        self.df = pd.DataFrame(columns=['text', 'score', 'time'])
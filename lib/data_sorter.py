import pandas as pd
import numpy as np
from datetime import datetime
import os, sys, re
from sqlalchemy import create_engine
from . import utils


class DataSorter:
    def __init__(self, params, logger):
        self.params = params
        self.logger = logger
    
    # Method to load from data list using web crawler
    # Should receive a comma seperated list
    def load_from_crawler(self, data):
        '''Load data from web crawler.
            Should receive a comma seperated list'''
        self.logger.info("Loading data from GPS Sport")
        for session in data:
            parsed_list = []
            # Decode from bytes array to string and split according to new line
            session = session.decode().split(',\r\n')
            for row in session:
                # Replace any commas located inside ", " so they don't get splitted later
                row = re.sub(',\s',  ' ', row).replace('"', '').split(',') 
                parsed_list.append(row)
            # get relevant data, columns names and data
            columns = parsed_list[:1]
            columns = [y for x in columns for y in x]
            rows = parsed_list[1:]
            df = pd.DataFrame(rows, columns=columns)
            df['Date'] = pd.to_datetime(df['Date'], infer_datetime_format=True, dayfirst=True)
            df.set_index('Date', inplace=True)
            self.sort_data(df, 'gps_data_parsed')
            self.logger.debug('Dataframe:')
            self.logger.debug(df)

    def load_from_csv(self, name):
        # Loading files from CSV
        self.logger.info('Loading from CSV')
        data_path = self.params['data_path']
        filename = self.params[name]['filename']
        filename_full_path = os.path.join(data_path, filename)
        index_col = self.params[name]['parse_config']['index_col']
        parse_dates = self.params[name]['parse_config']['parse_dates']
        day_first = self.params[name]['parse_config']['day_first']
        df = pd.read_csv(filename_full_path,
                            index_col = index_col,
                            parse_dates = parse_dates,
                            dayfirst = day_first)
        self.sort_data(df, name)
        self.logger.debug('Dataframe:')
        self.logger.debug(df)

    def sort_data(self, df, name):
        '''Standarize format'''
        
        self.logger.info('Sorting data')
        # Clean headers and sort index for faster sorting
        df.sort_index(inplace=True )
        df.reset_index(inplace=True)
        df.index = range(1,len(df)+1)
        df.fillna('', inplace=True)
        df.columns = [x.lower().strip().replace(' - ', '_').replace('-', '_').replace(' ', '_').replace('.', '').replace('(', '').replace(')', '') for x in df.columns]
        
        # GPS Data parsing
        if name == 'gps_data':
            numeric_columns = self.params['numeric_columns']
            str_columns = self.params['str_columns']
            players_alias_table = self.params['players']['tables'][0]
            players_table = self.params['players']['tables'][1]
            engine = self.connect_to_db()
            # read players from database
            players_df = pd.read_sql_query('select * from {}'.format(players_table), con=engine, index_col='id')
            related_names = pd.read_sql_query('select * from {}'.format(players_alias_table), con=engine, index_col='id')

            # Create players related names list so that we can standarize names
            df["athlete_id"] = df["athlete"].str.replace(' ', '').str.lower()

            # Change players names to id before inserting to database
            players_split = []
            for index in players_df.related_names_id:
                if related_names.iloc[index - 1].related_names != '': 
                    players_split = related_names.iloc[index - 1].related_names.split(',')
                    players_split = [x.replace(' ', '') for x in players_split]
                # add default name always
                default_name = players_df.iloc[index - 1].first_name + players_df.iloc[index - 1].last_name
                default_name = default_name.replace(' ', '')
                players_split.append(default_name)
                for alias in players_split:
                    df['athlete_id'] = df['athlete_id'].replace(alias, index)

            # Change dates columns to TimeStamp
            df['start_time'] = pd.to_datetime(df['start_time'], infer_datetime_format=True, dayfirst=True)

            # Change numeric columns to numeric vars
            for column in numeric_columns:
                df[column] = pd.to_numeric(df[column])
            
            # Create Agg dict for grouping
            agg_dict = {}
            for item in str_columns:
                agg_dict[item] = 'first'
            for item in numeric_columns:
                agg_dict[item] = 'sum'

            # Group by data, athlete, start time
            df = df.groupby(['date', 'athlete_id', 'start_time']).agg(agg_dict)
            df.reset_index(level=['athlete_id','start_time'], inplace=True)
            df.sort_index(inplace=True)
            # gps_data_df = df.copy()
            df.reset_index(inplace=True)
            db_table = self.params[name]['tables'][0]
            self.load_to_db(df, db_table)

        if name == 'players':
            # df['id'] = df.index
            df[['first_name','last_name1', 'last_name2']] = df['name'].str.split(' ', expand=True)
            df.fillna('', inplace=True)
            df['last_name'] = df['last_name1'] + ' ' + df['last_name2']
            # df['full_name'] = df['first_name'] + ' ' + df['last_name']
            for text_col in ['first_name', 'last_name', 'related_names']:
                df[text_col] = df[text_col].str.lower()
            df['related_names_id'] = df.index
            df['is_active'] = True

            players_df = df[['first_name', 'last_name', 'related_names_id', 'is_active']].copy()
            players_related_names = df[['related_names',]].copy()
            tables = [players_related_names, players_df]
            for counter, table_df in enumerate(tables):
                db_table = self.params[name]['tables'][counter]
                self.load_to_db(table_df, db_table)
        
        if name == 'injuries':
            self.logger.debug('CSV private config')
            tables = self.params[name]['tables']
            
            df.drop('index', axis=1, inplace=True)
            for table, column in tables.items():
                table_df = df[column].copy()
                table_df.replace('', np.nan, inplace=True)
                table_df.dropna(inplace=True)
                table_df.sort_values(by=column, inplace=True)
                table_df.reset_index(drop=True, inplace=True)     
                self.load_to_db(table_df, table)


    def load_to_db(self, table_df, db_table):
        print(table_df.head())
        self.logger.info('Loading table {} to DB'.format(db_table))
        engine = self.connect_to_db()
        table_df.to_sql(con=engine, name=db_table, if_exists='append', index=False)
        self.logger.info('Table loaded.')

        
        
        # if name == 'players_list':
        #     self.players_related_names.to_sql(con=engine, name='player_related_names', if_exists='append', index=False)
        #     self.players_df.to_sql(con=engine, name=players_table, if_exists='append', index=False)
        # if name == 'gps_data_parsed':
        #     self.gps_data_df.to_sql(con=engine, name=raw_data_table, if_exists='append', index=True)
    
    def connect_to_db(self):
        user = self.params['postgres']['user']
        password = self.params['postgres']['passwd']
        hostname = self.params['postgres']['host']
        raw_data_db = self.params['postgres']['raw_data_db']
        return create_engine('postgresql://{}:{}@{}/{}'.format(user, password, hostname, raw_data_db))

    # def data_to_ml(self):
    #     ml_db = self.params['postgres']['ml_db']

    def get_last_date(self):
        raw_data_table = self.params['postgres']['raw_data_table']
        engine = self.connect_to_db()
        df = pd.read_sql_query('select date from {} order by date desc limit 1'.format(raw_data_table), con=engine, index_col='date')
        last_date = df.index[0].date()
        current_date = datetime.now().date()
        time_delta = current_date - last_date

        if time_delta.days >= 1:
            days_to_download = time_delta.days
            return days_to_download
        return None
        




            
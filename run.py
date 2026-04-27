import os
from datetime import datetime, timedelta
import pandas as pd
import configparser

import yfinance as yf

from pgdb import PGDatabase

config = configparser.ConfigParser()
config.read('config.ini')

COMPANIES = eval(config['Companies']['COMPANIES'])
SALES_PATH = config['Files']['SALES_PATH']
DATABASE_CREDS = config['Database']

sales_df = pd.DataFrame()
if os.path.exists(SALES_PATH):
    sales_df = pd.read_csv(SALES_PATH)
    os.remove(SALES_PATH)
    

historical_d = {}
for company in COMPANIES:
    df = yf.download(
        company,
        start=(datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
        end=datetime.today().strftime("%Y-%m-%d"),
    )
    if not df.empty:
        # Сбрасываем индекс и упрощаем структуру
        df = df.reset_index()
        
        # Если колонки - MultiIndex, берем только первый уровень
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # Переименовываем колонки
        df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        
        # Убеждаемся, что Date - это datetime
        df['Date'] = pd.to_datetime(df['Date'])
        
        historical_d[company] = df

database = PGDatabase(
    host = DATABASE_CREDS["HOST"], 
    database = DATABASE_CREDS["DATABASE"],
    user = DATABASE_CREDS["USER"],
    password = DATABASE_CREDS["PASSWORD"]
)

for i, row in sales_df.iterrows():
    query = f"insert into sales values ('{row['dt']}', '{row['company']}', '{row['transaction_type']}', {row['amount']})"
    database.post(query)

for company, data in historical_d.items():
    if data.empty:
        continue
    
    for i, row in data.iterrows():
        # Форматируем дату
        date_str = row['Date'].strftime("%Y-%m-%d %H:%M:%S")
        
        # Берем значения напрямую
        open_val = row['Open']
        close_val = row['Close']
        
        # Формируем запрос
        query = f"INSERT INTO stock VALUES ('{date_str}', '{company}', {open_val}, {close_val})"
        
        try:
            database.post(query)
        except Exception as e:
            print(f"✗ Ошибка для {company}: {e}")
import argparse
import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
import io
import os
import re
from Ad import Ad
from pprint import pprint
import pytz
from datetime import datetime
import requests
import configparser
import json
import time
import threading
import pystray
from PIL import Image, ImageDraw


def on_clicked(icon, item):
    global IS_WORKING, TRAY
    IS_WORKING = False
    TRAY.stop()
    print("Программа завершена...")


def default_icon():
    # Generate an image
    width = 128
    height = 128
    color1 = "black"
    color2 = "white"
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)
    global ICON
    ICON = image


CONFIG = configparser.ConfigParser()
ICON_PATH = "CarsParser.ico"
ICON = None
if os.path.exists(ICON_PATH):
    ICON = Image.open(ICON_PATH)
else:
    default_icon()
TRAY = pystray.Icon('CarsParser', ICON, menu=pystray.Menu(
        pystray.MenuItem('Exit', on_clicked)))
SETTINGS_FILE = "settings.INI"
JSON_FILE = "cars.json"
URL = "https://www.sberleasing.ru/sbl-offers/?set_filter=y&sort=price&order=asc&PAGEN_1="
OUTPUT = "cars.csv"
PAGES = 3
WAIT_SEC = 1200
KEYWORDS = ["Skoda Rapid", "LADA (ВАЗ) Vesta"]
API_TOKEN = "6151132807:AAHWs6OK_RZhjxnRRIqYMLNydVfQKXg7jXg"
CHAT_ID_LIST = ["CHAT_ID_1", "CHAT_ID_2"]
AD_LIST = []
IS_WORKING = True


def run_tray():
    TRAY.run()


def run_parse():
    while IS_WORKING:
        result_list = parse()
        ads_save()
        export()
        send_to_telegram(result_list)
        time.sleep(WAIT_SEC)


def parse():
    result_list = []
    for i in range(1, PAGES + 1):
        # print(i)
        cur_url = f'{URL}{i}'
        r = requests.get(cur_url)
        if r.status_code is not 200:
            incorrect_url(cur_url)
            continue

        soup = bs(r.text, "html.parser")
        items = soup.find_all('a', class_='car-list__item')
        for item in items:
            url = 'https://www.sberleasing.ru/' + item['href']
            name = item.div.div.contents[0].strip()

            if not check(name, url): continue

            about = item.div.div.div.text.strip()
            props = item.find_all('div', class_='car-list__item-properties')[0].find_all('dl', class_='attrs-dotted')
            props_list = {}
            for prop in props:
                key = prop.dt.span.text.strip()
                value = prop.dd.text.strip()
                props_list[key] = value
            # pprint(props_list)
            vin = props_list['VIN']
            year = props_list['Год выпуска']
            mileage = props_list['Пробег, км']
            price = item.find_all('div', string=re.compile(' стоимость автомобиля '), )[0].parent.contents[0].replace("₽", "").replace(" ", "").strip()
            date = datetime.utcnow().replace(tzinfo=pytz.utc).strftime("%d.%M.%Y")
            ad = Ad(name, about, vin, year, mileage, price, url, date)
            result_list.append(ad)
            AD_LIST.append(ad)
    return result_list


def export():
    data = {'Модель': [], 'Описание': [], 'VIN': [], 'Год': [], 'Пробег': [], 'Цена': [], 'URL': [], 'Дата': []}
    for item in AD_LIST:
        data['Модель'].append(item.name)
        data['Описание'].append(item.about)
        data['VIN'].append(item.vin)
        data['Год'].append(item.year)
        data['Пробег'].append(item.mileage)
        data['Цена'].append(item.price)
        data['URL'].append(f'=HYPERLINK("{item.url}")')
        data['Дата'].append(item.date)
    df = pd.DataFrame(data=data)
    try:
        df.to_csv(OUTPUT, encoding='cp1251', sep='|', index=False)
        with io.open(OUTPUT, "r+", encoding='cp1251') as f:
            content = f.read()
            f.seek(0, 0)
            f.write("sep=|\r" + content)
    except Exception as e:
        print(f"{OUTPUT} is open in another application")


def send_to_telegram(list):
    apiURL = f'https://api.telegram.org/bot{API_TOKEN}/sendMessage'

    for item in list:
        message = f"\n{item.get_for_send()}"
        for id in CHAT_ID_LIST:
            try:
                response = requests.post(apiURL, json={'chat_id': id, 'text': message})
                # print(response.text)
            except Exception as e:
                print(e)


def get_config():
    global URL, OUTPUT, PAGES, KEYWORDS, API_TOKEN, CHAT_ID_LIST, WAIT_SEC
    if os.path.exists(SETTINGS_FILE):
        CONFIG.read(SETTINGS_FILE, encoding='cp1251')
        URL = get_config_value('CONFIG', 'url', URL)
        PAGES = int(get_config_value('CONFIG', 'pages', PAGES))
        KEYWORDS = get_config_value('CONFIG', 'keywords', ", ".join(x for x in KEYWORDS)).split(", ")
        WAIT_SEC = int(get_config_value('CONFIG', 'wait_sec', WAIT_SEC))
        OUTPUT = get_config_value('CONFIG', 'output', OUTPUT)
        API_TOKEN = get_config_value('CONFIG', 'apy_token', API_TOKEN)
        CHAT_ID_LIST = get_config_value('CONFIG', 'chat_id_list', ", ".join(x for x in CHAT_ID_LIST)).split(", ")
    else:
        URL = safe_input(f'Введите в кавычках URL без номера страницы и нажимете Enter...\nПо-умолчанию: "{URL}"', str,
                         URL)
        PAGES = safe_input(f'Введите номер последней просматриваемой страницы и нажимете Enter...\nПо-умолчанию: {PAGES}', int, PAGES)
        KEYWORDS = safe_input(f'Введите через запятую ключевые слова в кавычках и нажимете Enter...\nПо-умолчанию: {", ".join(x for x in KEYWORDS)}', list, KEYWORDS)
        WAIT_SEC = safe_input(f'Введите задержку между запросами в секундах и нажимете Enter...\nПо-умолчанию: {WAIT_SEC}', int, WAIT_SEC)
        OUTPUT = safe_input(f'Введите название файла для сохранения таблицы объявлений и нажимете Enter...\nПо-умолчанию: "{OUTPUT}"', str, OUTPUT)
        API_TOKEN = safe_input(f'Введите название файла для сохранения таблицы объявлений и нажимете Enter...\nПо-умолчанию: "{API_TOKEN}"', str, API_TOKEN)
        CHAT_ID_LIST = safe_input(f'Введите через запятую CHAT_ID в кавычках и нажимете Enter...\nПо-умолчанию: {", ".join(x for x in CHAT_ID_LIST)}\nЧтобы найти свой CHAT_ID, напишите в чат бота и откройте https://api.telegram.org/bot6151132807:AAHWs6OK_RZhjxnRRIqYMLNydVfQKXg7jXg/getUpdates', list, CHAT_ID_LIST)


def set_config():
    if not CONFIG.has_section('CONFIG'):
        CONFIG.add_section('CONFIG')
    CONFIG['CONFIG']['url'] = URL
    CONFIG['CONFIG']['output'] = OUTPUT
    CONFIG['CONFIG']['pages'] = str(PAGES)
    CONFIG['CONFIG']['keywords'] = ", ".join(x for x in KEYWORDS)
    CONFIG['CONFIG']['wait_sec'] = str(WAIT_SEC)
    CONFIG['CONFIG']['apy_token'] = API_TOKEN
    CONFIG['CONFIG']['chat_id_list'] = ", ".join(x for x in CHAT_ID_LIST)

    with open(SETTINGS_FILE, 'w', encoding='cp1251') as configfile:  # save
        CONFIG.write(configfile)


def safe_input(text, type, default):
    result = None
    while True:
        try:
            value = input(text+"\n\n>")
            if value is None or value == "":
                result = default
                break
            if type == str:
                result = value
            if type == int:
                result = int(value)
            if type == list:
                result = value.replace(" ", "").split(",")
            break
        except Exception as e:
            print("Данные введены неккоректно")
    return result


def get_config_value(section, option, default):
    if CONFIG.has_section(section):
        if CONFIG.has_option(section, option):
            return CONFIG[section][option]
    return default


def ads_save():
    with open(JSON_FILE, 'w') as f:
        # indent=2 is not needed but makes the file human-readable
        # if the data is nested
        json.dump([obj.__dict__ for obj in AD_LIST], f, indent=4)


def ads_read():
    if os.path.exists(JSON_FILE):
        global AD_LIST
        with open(JSON_FILE, 'r') as f:
            AD_LIST = json.load(f, object_hook=lambda d: Ad(**d))


def check(name, url):
    if any(s.lower() in name.lower() for s in KEYWORDS):
        if not any(obj.url == url for obj in AD_LIST):
            return True
    return False


def incorrect_url(url):
    print(f"incorrect url: {url}")


def parsing_faild():
    print("parsing faild")


if __name__ == '__main__':  # Если мы запускаем файл напрямую, а не импортируем
    get_config()
    set_config()
    ads_read()
    ThreadParse = threading.Thread(target=run_parse)
    ThreadParse.start()
    run_tray()
    # ThreadTray.join()  # wait for thread to stop
    # ThreadParse.join()  # wait for thread to stop

import locale
import json
locale.setlocale(locale.LC_ALL, 'ru_ru.UTF-8')

class Ad(object):

    def __init__(self, name, about, vin, year, mileage, price, url, date):
        self.name = name
        self.about = about
        self.vin = vin
        self.year = year
        self.mileage = mileage
        self.price = price
        self.url = url
        self.date = date

    def __str__(self):
        return f"{self.name}, {self.about}, {self.vin}, {self.year}, {self.mileage}, {self.price}, {self.url}, {self.date}"

    def __repr__(self):
        return self.__str__()

    def get_for_send(self):
        return f"{self.name} {self.about} ({self.year})\nVIN:  {self.vin}\nПробег:  {'{0:,}'.format(int(self.mileage)).replace(',', ' ')} км.\n" \
               f"Цена:  {locale.currency(int(self.price), grouping=True )}\n\n{self.url}"

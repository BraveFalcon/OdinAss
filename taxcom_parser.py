import requests
from currency import Currency


def get_items(qr_data):
    url = "https://receipt.taxcom.ru/v01/show?" + qr_data[qr_data.find('&') + 1:]
    request = requests.get(url)

    if request.status_code == 404:
        print("Can't connect with taxcom")
        return []

    content = request.content.decode("utf-8")
    if "Чек по указанным параметрам не найден" in content:
        return []

    items = []
    lines = content.split('\n')
    i = 0

    def __get_number(string):
        return string[55:string[55:].find("/") + 54]

    while i < len(lines):
        if lines[i].strip() == """<span class="value receipt-value-1030">""":
            name = lines[i + 1].strip()
            quantity = __get_number(lines[i + 10])
            price = __get_number(lines[i + 12])
            cost = __get_number(lines[i + 15])
            items.append([name + ': ' + quantity + " * " + price + " = ", Currency(cost)])
            i += 49
        else:
            i += 1
    return items

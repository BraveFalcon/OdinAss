import requests
from Currency import Currency


def get_items(fiscal_id, receipt_sum):
    url = "https://receipt.taxcom.ru/v01/show?fp={}&s={}".format(
        fiscal_id,
        receipt_sum
    )
    request = requests.get(url)

    if request.status_code == 404:
        print("Can't connect with taxcom")
        return []

    content = request.content.decode("utf-8")
    if "Чек по указанным параметрам не найден" in content:
        print("Receipt not found! Check the correctness of the entered data")
        return []

    items = []
    lines = content.split('\n')
    i = 0

    def __get_number(string):
        return string[55:string[55:].find("/") + 54]

    while i < len(lines):
        if lines[i].strip() == """<span class="value receipt-value-1030">""":
            name = lines[i + 1].strip()
            quantity = __get_number(lines[i + 9])
            price = __get_number(lines[i + 11])
            cost = __get_number(lines[i + 14])
            items.append([name + ': ' + quantity + " * " + price + " = ", Currency(cost)])
            i += 49
        else:
            i += 1
    return items

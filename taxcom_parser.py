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
    for i in range(len(lines)):
        if lines[i].strip() == """<span class="value receipt-value-1030">""":
            items.append([lines[i + 1].strip()])
        if """<span class="value receipt-value-1043">""" in lines[i]:
            begin = lines[i].find("\">") + 2
            end = lines[i].find("</span>")
            items[-1].append(Currency(lines[i][begin:end]))
    return items

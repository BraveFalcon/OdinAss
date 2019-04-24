from Bot import Bot

def main():
    b = Bot(open("key.txt").read().strip().split())

    #b.load()
    #print(b.get_answers())

    b.process_receipt(2335510205, 357.09)
    b.save()

if __name__ == "__main__":
    main()

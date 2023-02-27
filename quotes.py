import datetime
import numpy as np


def save_quote(text):
    """Save a quote to file given a message"""
    if text[:4] == "&gt;":
        text = text.replace("&gt;", "").replace("\"", "").replace("“", "").replace("”", "")
        the_quote, the_person = text.split("-")
        the_quote, the_person = the_quote.strip(), the_person.strip()

        with open("private_data/quotes.txt", "r") as f:
            file = f.read()
            lines = file.split("}")

        for line in lines:
            if line.rstrip() != "":
                latest_id, _, _, _ = line.lstrip().rstrip().split("|")

        with open("private_data/quotes.txt", "a") as f:
            f.writelines([f"\n{int(latest_id) + 1}|{the_quote}|{the_person}|1900-01-01" + "}"])


def pick_random_quote():
    with open("private_data/quotes.txt", "r") as f:
        file = f.read()
        lines = file.split("}")

    ids, quotes, people = [], [], []
    today = datetime.date.today()
    for line in lines:
        if line.rstrip() != "":
            id, quote, person, date = line.split("|")
            year, month, day = date.split("-")

            dt = datetime.date(year=int(year), month=int(month), day=int(day))
            days_since = (today - dt).days

            if days_since > 100:
                ids.append(id)
                quotes.append(quote)
                people.append(person)

    if len(ids) == 0:
        return None, None

    i = np.random.randint(len(ids))
    lines[int(ids[i])] = f"{ids[i]}|{quotes[i]}|{people[i]}|{today.year}-{today.month}-{today.day}" + "\n"
    for j in range(len(lines)):
        if lines[j] != "":
            lines[j] = lines[j].replace("\n", "") + "}\n"

    with open("private_data/quotes.txt", "w") as f:
        f.writelines(lines)

    return quotes[i], people[i]

# with open("private_data/quotes.txt", "r") as f:
#     lines = f.readlines()
# for i in range(len(lines)):
#     lines[i] = lines[i].replace("\n", "}\n")
# with open("private_data/quotes.txt", "w") as f:
#     f.writelines(lines)


# with open("private_data/quotes.txt", "r") as f:
#     file = f.read()
#     lines = file.split("}")

# print(len(lines))
# print(lines[0])

# for line in lines:
#     if line.rstrip() != "":
#         print(line, line.lstrip().rstrip().split("|"))
#         latest_id, _, _, _ = line.lstrip().rstrip().split("|")
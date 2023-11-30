import datetime
import pandas as pd


def save_quote(text):
    """Save a quote to file given a message"""
    # check if the message is a quote
    if text[:4] == "&gt;":
        # remove the quote symbols and quotation marks
        text = text.replace("&gt;", "").replace("\"", "").replace("“", "").replace("”", "")

        # split the quote and person
        the_quote, the_person = text.split("-")
        the_quote, the_person = the_quote.strip(), the_person.strip()

        # append the quote to the quotes file
        quotes = pd.read_csv("private_data/quotes.csv", sep="|")
        quotes.append({'quote': the_quote,
                       'person': the_person,
                       'date': pd.Timestamp("1900-01-01")},
                      ignore_index=True).reset_index().to_csv("private_data/quotes.csv",
                                                              sep="|", index=False)


def pick_random_quote():
    quotes = pd.read_csv("private_data/quotes.csv", sep="|")

    # find which quotes have not been used in the last 100 days
    today = datetime.date.today()
    unrecent_quotes = pd.to_datetime(quotes["date"]) < (pd.Timestamp(today) - pd.Timedelta(days=100))

    # if all quotes have been used in the last 100 days, return None
    if unrecent_quotes.sum() == 0:
        return None, None

    # pick a random quote from the unrecent quotes
    random_quote = quotes[unrecent_quotes].sample(1)

    # update the quote date to today
    quotes.loc[random_quote.index, "date"] = pd.Timestamp(today)
    quotes.to_csv("private_data/quotes.csv", sep="|")

    # return the quote and person
    return random_quote["quote"].values[0], random_quote["person"].values[0]

import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError
import re
import numpy as np
import datetime

from apscheduler.schedulers.background import BackgroundScheduler

# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
GERALD_ID = "U03SY9R6D5X"


""" ---------- MESSAGE DETECTIONS ---------- """


@app.event("message")
def handle_message_events(body, logger):
    # print("I detected a message", body)
    logger.info(body)

    message = body["event"]

    reaction_trigger(message, "tom", "tom")
    reaction_trigger(message, "undergrad", "underage")
    reaction_trigger(message, "gerald", ["gerald", "eyes"])
    reaction_trigger(message, "birthday", ["birthday", "tada"])
    reaction_trigger(message, "panic", ["mildpanic"])
    reaction_trigger(message, "PANIC", ["mild-panic-intensifies"], case_sensitive=True)

    msg_action_trigger(message, "bonk", bonk_someone)


def bonk_someone(message):
    # find the user to bonk
    bonkers = re.search("\<(.*?)\>", message["text"])

    # if there is one then BONK them
    if bonkers is not None:
        person_to_bonk = bonkers[0]

        followups = ["Now go and think about what you've done!",
                     "Bad grad student, I'll take away your :coffee:!",
                     "You're lucky Asimov made that first law mate...:robot_face::skull:",
                     "There's more where that came from"]
        followup = np.random.choice(followups)

        app.client.chat_postMessage(text=f"BONK {person_to_bonk} :bonk::bonk:\n" + followup,
                                    thread_ts=message["ts"], channel=message["channel"])
    else:
        app.client.chat_postMessage(text="I couldn't work out who to bonk :sob:",
                                    thread_ts=message["ts"], channel=message["channel"])


def msg_action_trigger(message, triggers, callback, case_sensitive=False):
    triggers = np.atleast_1d(triggers)
    text = message["text"] if case_sensitive else message["text"].lower()

    for trigger in triggers:
        if text.find(trigger) >= 0:
            callback(message)


""" ---------- MESSAGE REACTIONS ---------- """


def reaction_trigger(message, triggers, reactions, case_sensitive=False):
    triggers = np.atleast_1d(triggers)
    reactions = np.atleast_1d(reactions)
    text = message["text"] if case_sensitive else message["text"].lower()

    for trigger in triggers:
        if text.find(trigger) >= 0:
            for reaction in reactions:
                app.client.reactions_add(
                    channel=message["channel"],
                    timestamp=message["ts"],
                    name=reaction
                )

""" ---------- WHINETIME ---------- """


@app.view("whinetime-modal")
def whinetime_submit(ack, body, say, client, logger):
    # acknowledge the submission
    ack()

    # get the values from the form
    state = body["view"]["state"]["values"]
    location = state["whinetime-location"]["whinetime-location"]["value"]
    date = state["whinetime-date"]["datepicker-action"]["selected_date"]
    time = state["whinetime-time"]["timepicker-action"]["selected_time"]

    ch_id = find_channel("bot-test")

    # convert the information to a datetime object
    year, month, day = list(map(int, date.split("-")))
    hour, minute = list(map(int, time.split(":")))
    dt = datetime.datetime(year, month, day, hour, minute)

    # format it nicely
    formatted_date = custom_strftime("%A (%B {S}) at %I:%M%p", dt)

    # send out an initial message to tell people the plan and ask for reactions
    say(f"Okay folks, we're good to go! Whinetime will happen on {formatted_date} at {location}. I'll remind you closer to the time but now react to this message with :beers: if you're coming!", channel=ch_id)

    # calculate some timestamps in the future (I hope)
    day_before = (dt - datetime.timedelta(days=1)).strftime("%s")
    hour_before = (dt - datetime.timedelta(hours=1)).strftime("%s")

    # attempt to send reminders (using Try because people may be too close to the time)
    try:
        result = client.chat_scheduleMessage(
            channel=ch_id,
            text="Only one day to go until #whinetime! Don't forget to react to the message above if you're coming",
            post_at=day_before
        )
        logger.info(result)

    except SlackApiError as e:
        logger.error("Error scheduling message: {}".format(e))

    try:
        result = client.chat_scheduleMessage(
            channel=ch_id,
            text=f"Feeling that Friday afternoon fatigue? You need some #whinetime mate and luckily it's only one hour to go :meowparty::meowparty: Remember it's at {location} this week, hope you guys have fun!",
            post_at=hour_before
        )
        logger.info(result)

    except SlackApiError as e:
        logger.error("Error scheduling message: {}".format(e))


@app.action("whinetime-open")
def whinetime_logistics(body, client):
    # open the modal when someone clicks the button
    client.views_open(trigger_id=body["trigger_id"], view={
        "callback_id": "whinetime-modal",
        "title": {
            "type": "plain_text",
            "text": "Whinetime logistics",
            "emoji": True
        },
        "submit": {
            "type": "plain_text",
            "text": "Submit",
            "emoji": True
        },
        "type": "modal",
        "close": {
            "type": "plain_text",
            "text": "Cancel",
            "emoji": True
        },
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Whinetime (Week of {datetime.datetime.now().strftime('%d/%m/%y')})",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Okay you're the boss, what's the plan? Let me know and I'll send reminders out for whinetime!"
                }
            },
            {
                "type": "input",
                "block_id": "whinetime-location",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "whinetime-location"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Where shall we go?",
                    "emoji": True
                }
            },
            {
                "type": "input",
                "block_id": "whinetime-date",
                "element": {
                    "type": "datepicker",
                    "initial_date": "2022-08-05",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a date",
                        "emoji": True
                    },
                    "action_id": "datepicker-action"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Which day?",
                    "emoji": True
                }
            },
            {
                "type": "input",
                "block_id": "whinetime-time",
                "element": {
                    "type": "timepicker",
                    "initial_time": "17:00",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select time",
                        "emoji": True
                    },
                    "action_id": "timepicker-action"
                },
                "label": {
                    "type": "plain_text",
                    "text": "What time?",
                    "emoji": True
                }
            }
        ]
    })


@app.action("whinetime-re-roll")
def whinetime_re_roll(ack, body, logger):
    ack()
    logger.info(body)
    app.client.chat_delete(channel=body["container"]["channel_id"], ts=body["container"]["message_ts"])
    start_whinetime_workflow(reroll=True, not_these=body["actions"][0]["value"].split(","))


def start_whinetime_workflow(reroll=False, not_these=[GERALD_ID]):
    ch_id = find_channel("bot-test")

    # get all of the members in the channel
    members = app.client.conversations_members(channel=ch_id)["members"]

    # choose someone random (but NOT Gerald lol)
    members = list(set(members) - set([GERALD_ID]) - set(not_these))
    if members == []:
        app.client.chat_postMessage(text=("Uh oh, I've tried everyone in the channel and it seems no one is "
                                          "free to host! :smiling_face_with_tear:"), channel=ch_id)
        return

    random_member = np.random.choice(members)
    not_these.append(random_member)

    if not reroll:
        app.client.chat_postMessage(text=("Dumroll please :drum_with_drumsticks:...it's time to pick a "
                                          "whinetime host"), channel=ch_id)
    else:
        messages = [("Not whinetime eh? Are you sure? You could be great, you know, whinetime will help you "
                     "on the way to greatness, no doubt about that — no? Well, if you're sure — better "
                     f"be ~GRYFFINDOR~ <@{random_member}>!"),
                    "Okay let's try that again, your whinetime host will be...:drum_with_drumsticks:",
                    "Okay let's try that again, your whinetime host will be...:drum_with_drumsticks:",
                    "Nevermind, let's choose someone else, how about...:drum_with_drumsticks:"]
        app.client.chat_postMessage(text=np.random.choice(messages).replace("\n", " "), channel=ch_id)

    # post the announcement
    app.client.chat_postMessage(channel=ch_id, blocks=[
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Whinetime (Week of {datetime.datetime.now().strftime('%d/%m/%y')})",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Okay <@{random_member}>, you're the boss, what's the plan?"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Setup logistics",
                        "emoji": True
                    },
                    "value": "none",
                    "action_id": "whinetime-open"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Choose someone else!",
                        "emoji": True
                    },
                    "value": ",".join(not_these),
                    "action_id": "whinetime-re-roll",
                    "style": "danger",
                    "confirm": {
                        "title": {
                            "type": "plain_text",
                            "text": "Are you sure?"
                        },
                        "text": {
                            "type": "mrkdwn",
                            "text": "Wouldn't you rather be relaxing at whinetime :pleading_face:?"
                        },
                        "confirm": {
                            "type": "plain_text",
                            "text": "Do it"
                        },
                        "deny": {
                            "type": "plain_text",
                            "text": "Stop, I've changed my mind!"
                        }
                    },
                }
            ]
        },
    ])


""" ---------- BIRTHDAYS ---------- """


def say_happy_birthday(user_id):
    """Say happy birthday to a particular user

    Parameters
    ----------
    user_id : `str`
        Slack ID of the user
    """
    # pick a random GIF from the collection
    gif_id = np.random.randint(0, 7 + 1)
    gif_url = f"https://raw.githubusercontent.com/TomWagg/gerald/main/img/birthday_gifs/{gif_id}.gif"

    # post the message with the GIF
    app.client.chat_postMessage(channel=find_channel("bot-test"),
                                text=f":birthday: Happy birthday to <@{user_id}>! :birthday:",
                                blocks=[
                                    {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": f":birthday: Happy birthday to <@{user_id}>! :birthday:",
                                        }
                                    },
                                    {
                                        "type": "image",
                                        "image_url": gif_url,
                                        "alt_text": "birthday"
                                    }
                                ])


def get_all_birthdays():
    """Get a list of all of the birthdays

    Returns
    -------
    info : `list of tuples`
        List of name, birthday pairs. Birthday is None if it's not in the table
    """
    # open the file with the birthdays
    info = []
    with open("data/birthday_phone_list.csv") as birthday_file:
        for grad in birthday_file:
            # ignore any comment lines
            if grad[0] == "#":
                continue
            name, _, _, birthday, _ = grad.split(",")

            # if we don't have their birthday just write None
            if birthday.rstrip() == "-":
                info.append((name, None))
            # otherwise format the birthday nicely
            else:
                day, month = map(int, birthday.rstrip().split("/"))
                birthday_dt = datetime.date(year=2022, month=month, day=day)
                info.append((name, custom_strftime("%B {S}", birthday_dt)))
    return info


def is_it_a_birthday():
    """ Check if today is someone's birthday! """
    # find the closest birthday
    birthday_people, _, closest_time = closest_birthday()

    # if you found someone and their birthday is today
    if birthday_people != [] and closest_time == 0:
        # get the list of users in the workspace
        users = app.client.users_list()["members"]
        for user in users:
            for person in birthday_people:
                # say happy birthday to each person (handle if there are more than one)
                if user["name"] == person:
                    say_happy_birthday(user["id"])


def closest_birthday():
    """ Work out when the closest birthday to today is """
    today = datetime.date.today()

    usernames = []
    names = []
    closest_time = np.inf

    # go through the birthday list
    with open("data/birthday_phone_list.csv") as birthdays:
        for grad in birthdays:
            # ignore comment lines
            if grad[0] == "#":
                continue
            name, username, _, birthday, _ = grad.split(",")

            # ignore people without birthdays listed
            if birthday.rstrip() == "-":
                continue

            # work out the year based on the month and day
            day, month = map(int, birthday.rstrip().split("/"))
            if month < today.month or (month == today.month and day < today.day):
                year = today.year + 1
            else:
                year = today.year

            # work out the days until the birthday
            birthday_dt = datetime.date(year=year, month=month, day=day)
            days_until = (birthday_dt - today).days

            # if it's sooner than the current closest then replace it
            if days_until < closest_time:
                usernames = [username]
                names = [name]
                closest_time = days_until
            # if it is equal then we have two people sharing a birthday!
            elif days_until == closest_time:
                usernames.append(username)
                names.append(name)
    return usernames, names, closest_time


""" ---------- APP MENTIONS ---------- """


@app.event("app_mention")
def reply_to_mentions(say, body):
    # reply to mentions with specific messages
    for triggers, response in zip([["status", "okay", "ok", "how are you"],
                                   ["thank", "you're the best", "nice job", "good work", "good job"],
                                   ["celebrate"]],
                                  ["Don't worry, I'm okay. In fact, I'm feeling positively tremendous old bean!",
                                   ["You're welcome!", "My pleasure!", "Happy to help!"],
                                   [":tada::meowparty: WOOP WOOP :meowparty::tada:"]]):
        did_not_reply = mention_trigger(message=body["event"]["text"], triggers=triggers, response=response,
                                        thread_ts=body["event"]["ts"], ch_id=body["event"]["channel"])
        if not did_not_reply:
            return

    # set up some manual checks
    # TODO: functionise this
    if body["event"]["text"].find("WHINETIME MANUAL") >= 0:
        start_whinetime_workflow()
    elif body["event"]["text"].find("BIRTHDAY MANUAL") >= 0:
        is_it_a_birthday()
    elif (body["event"]["text"].lower().find("next") >= 0 and body["event"]["text"].lower().find("birthday") >= 0):
        _, names, closest_time = closest_birthday()

        time_until_str = f"it's in {closest_time} days!" if closest_time != 0 else "it's today :scream:!!"

        if len(names) == 1:
            say(text=f"The next person to have a birthday is {names[0]} and " + time_until_str,
                channel=body["event"]["channel"], thread_ts=body["event"]["ts"])
        else:
            message = "The next people to have birthdays are " + " AND ".join(names) + " and "
            message += time_until_str
            say(text=message, channel=body["event"]["channel"], thread_ts=body["event"]["ts"])
    elif ((body["event"]["text"].lower().find("everyone") >= 0
           or body["event"]["text"].lower().find("all") >= 0)
          and body["event"]["text"].lower().find("birthday") >= 0):
        info = get_all_birthdays()

        unknowns = ""
        knowns = ""

        for name, birthday in info:
            if birthday is None:
                unknowns += f"• {name}\n"
            else:
                knowns += f"• {name} - {birthday}\n"

        message = ":birthday: Here's a list of birthdays that I know\n" + knowns
        message += "\n:question: And here's a list of people I know but whose birthdays I don't\n" + unknowns

        say(text=message.rstrip(), channel=body["event"]["channel"], thread_ts=body["event"]["ts"])
    else:
        say(text=("Okay, good news: I heard you, bad news: I'm not a very smart bot so I don't know what you"
                  "want from me :shrug::baby::robot_face:"),
            thread_ts=body["event"]["ts"], channel=body["event"]["channel"])


def mention_trigger(message, triggers, response, thread_ts=None, ch_id=None, case_sensitive=False):
    """Respond to a mention of the app based on certain triggers

    Parameters
    ----------
    message : `str`
        The message that mentioned the app
    triggers : `list`
        List of potential triggers
    response : `list` or `str`
        Either a list of responses (a random will be chosen) or a single response
    thread_ts : `float`, optional
        Timestamp of the thread of the message, by default None
    ch_id : `str`, optional
        ID of the channel, by default None
    case_sensitive : `bool`, optional
        Whether the triggers are case sensitive, by default False

    Returns
    -------
    no_matches : `bool`
        Whether there were no matches to the trigger or not
    """
    # keep track of whether you found a match to a trigger
    no_matches = True

    # move it all to lower case if you don't care
    if not case_sensitive:
        message = message.lower()

    # go through each potential trigger
    for trigger in triggers:
        # if you find it in the message
        if message.find(trigger) >= 0:
            no_matches = False

            # if the response is a list then pick a random one
            if isinstance(response, list):
                response = np.random.choice(response)

            # send a message and break out
            app.client.chat_postMessage(channel=ch_id, text=response, thread_ts=thread_ts)
            break
    return no_matches


""" ---------- EMOJI HANDLING ---------- """


@app.event("emoji_changed")
def new_emoji(body, say):
    if body["event"]["subtype"] == "add":
        emoji_add_messages = ["I'd love to know the backstory on that one",
                              "Anyone want to explain this??",
                              "Feel free to put it to use on this message",
                              "Looks like I've found my new favourite",
                              "And that's all the context you're getting"]
        rand_msg = emoji_add_messages[np.random.randint(len(emoji_add_messages))]

        ch_id = find_channel("bot-test")
        say(f'Someone just added :{body["event"]["name"]}: - {rand_msg}', channel=ch_id)


""" ---------- HELPER FUNCTIONS ---------- """


def find_channel(channel_name):
    """Find the ID of a slack channel

    Parameters
    ----------
    channel_name : `str`
        Name of the Slack channel

    Returns
    -------
    ch_id : `str`
        ID of the Slack channel
    """
    # grab the list of channels
    channels = app.client.conversations_list(exclude_archived=True)
    ch_id = None

    # go through each and find one with the same name
    for channel in channels["channels"]:
        if channel["name"] == channel_name:
            # save the ID and break
            ch_id = channel["id"]
            break

    # if you didn't find one then send out a warning (who changed the channel name!?)
    if ch_id is None:
        print(f"WARNING: couldn't find channel '{channel_name}'")
    return ch_id


def suffix(d):
    """ Work out what suffix a date needs """
    return 'th' if 11 <= d <= 13 else {1: 'st',2: 'nd',3: 'rd'}.get(d % 10, 'th')


def custom_strftime(format, t):
    """ Change the default datetime strftime to use the custom suffix """
    return t.strftime(format).replace('{S}', str(t.day) + suffix(t.day))


def every_morning():
    """ This function runs every morning around 9AM """
    today = datetime.datetime.now()
    the_day = today.strftime("%A")

    # if the day is Monday then send out the whinetime reminders
    if the_day == "Monday":
        start_whinetime_workflow()

    is_it_a_birthday()


# start Gerald
if __name__ == "__main__":
    scheduler = BackgroundScheduler({'apscheduler.timezone': 'US/Pacific'})
    scheduler.add_job(every_morning, "cron", hour=9, minute=32)
    scheduler.start()
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()

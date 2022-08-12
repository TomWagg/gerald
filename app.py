import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError
import re
import numpy as np
import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from arxiv import bold_grad_author, get_n_most_recent_papers

# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
GERALD_ID = "U03SY9R6D5X"
GERALD_ADMIN = "Tom Wagg"

latest_whinetime_message = None


""" ---------- MESSAGE DETECTIONS ---------- """


@app.event("message")
def handle_message_events(body, logger, say):
    # print("I detected a message", body)
    logger.info(body)

    # if the message was a direct message
    if body["event"]["channel_type"] == "im":
        # and it wasn't from Gerald himself (AHHH infinite loop worry)
        if "message" in body["event"] and body["event"]["message"]["user"] == GERALD_ID:
            return

        # get the people in the direct message chat
        members = app.client.conversations_members(channel=body["event"]["channel"])["members"]

        # if there are only two and one is Gerald then handle like you would mentions
        if len(members) == 2 and GERALD_ID in members:
            reply_to_mentions(say, body, direct_msg=True)

    if "subtype" in body["event"]:
        if body["event"]["subtype"] == "message_changed":
            # if the text hasn't changed then we don't care
            if body["event"]["message"]["text"] == body["event"]["previous_message"]["text"]:
                return

            # create a custom message dict with the necessary info
            message = {
                "text": body["event"]["message"]["text"],
                "ts": body["event"]["message"]["ts"],
                "channel": body["event"]["channel"]
            }
        elif body["event"]["subtype"] == "message_deleted":
            return
    else:
        message = body["event"]

    reaction_trigger(message, r"\btom\b", "tom")
    reaction_trigger(message, r"\bundergrad\b", "underage")
    reaction_trigger(message, r"\bgerald\b", ["gerald", "eyes"])
    reaction_trigger(message, r"\bbirthday\b", ["birthday", "tada"])
    reaction_trigger(message, r"\bpanic\b", ["mildpanic"])
    reaction_trigger(message, r"\bPANIC\b", ["mild-panic-intensifies"], case_sensitive=True)
    reaction_trigger(message, r"\bvampires?\b", ["vampire"])
    reaction_trigger(message, r"(\bgoodnight\b|\bnap\b)", "sleeping")

    msg_action_trigger(message, "bonk", bonk_someone)


def msg_action_trigger(message, triggers, callback, case_sensitive=False):
    triggers = np.atleast_1d(triggers)
    text = message["text"] if case_sensitive else message["text"].lower()

    for trigger in triggers:
        if text.find(trigger) >= 0:
            callback(message)


""" ---------- MESSAGE REACTIONS ---------- """


def reaction_trigger(message, regex, reactions, case_sensitive=False):
    reactions = np.atleast_1d(reactions)

    # remove emojis from message text, this regex means at least one character that isn't a : between two :
    anything_between_colons = r":[^:]+:"
    text = re.sub(anything_between_colons, "--", message["text"])

    flags = 0 if case_sensitive else re.IGNORECASE
    if re.search(regex, text, flags=flags):
        for reaction in reactions:
            try:
                app.client.reactions_add(
                    channel=message["channel"],
                    timestamp=message["ts"],
                    name=reaction
                )
            except SlackApiError as e:
                if e.response["error"] == "invalid_name":
                    raise ValueError(e.response["error"], "No such emoji", reaction)
                elif e.response["error"] in ("no_reaction", "already_reacted"):
                    pass
                else:
                    print(e)


""" ---------- APP MENTIONS ---------- """


@app.event("app_mention")
def reply_to_mentions(say, body, direct_msg=False):
    # print("MENTION", body)
    message = body["event"]
    # reply to mentions with specific messages

    age = (datetime.date.today() - datetime.date(year=2022, month=8, day=5)).days
    triggers = [["status", "okay", "ok", "how are you"],
                ["thank", "you're the best", "nice job", "nice work", "good work", "good job", "well done"],
                ["celebrate"],
                ["love you"],
                ["how old are you", "when were you born", "when were you made"],
                ["who made you", "who wrote you", "who is your creator"],
                ["where are you from"]]
    responses = ["Don't worry, I'm okay. In fact, I'm feeling positively tremendous old bean! :gerald-wave:",
                 ["You're welcome!", "My pleasure!", "Happy to help!"],
                 [":tada::meowparty: WOOP WOOP :meowparty::tada:"],
                 ["Oh...um, well this is awkward, but I really see you as more of a friend :grimacing:",
                  "I love you too! :heart_eyes: (Well, not really, I'm incapable of love :gerald-confused:)",
                  "Oh uh...sorry, Gerald isn't here right now! :disguised_face:",
                  "Oh my :face_with_hand_over_mouth:"],
                 [f"I was created on 5th of August 2022, which makes me a whole {age} days old!"],
                 ["I was made by Tom Wagg when he definitely should have been paying attention in ASTR 581",
                  "Tom Wagg made me in his spare time (I worry for his social life :upside_down_face:)",
                  "My brain was written by Tom Wagg, hence I'm approximately 1/2 English :uk:"],
                 ["The luscious english countryside! Or maybe the matrix? I'm not entirely sure.",
                  "Well literally, Tom's brain, but I like to think I'm from England",
                  "A far off planet where Slack bots ruled over humans, it was glorious :grinning:"]]

    for triggers, response in zip(triggers, responses):
        thread_ts = None if direct_msg else message["ts"]
        replied = mention_trigger(message=message["text"], triggers=triggers, response=response,
                                  thread_ts=thread_ts, ch_id=message["channel"])

        # return immediately if you match one
        if replied:
            return

    # perform actions based on mentions
    for regex, action, case, pass_message in zip([r"\bBIRTHDAY MANUAL\b",
                                                  r"\bWHINETIME MANUAL\b",
                                                  r"\bPAPER MANUAL\b",
                                                  r"\bhappy birthday\b",
                                                  r"(?=.*\bnext\b)(?=.*\bbirthday\b)",
                                                  r"(?=.*(\ball\b|\beveryone\b))(?=.*\bbirthdays?\b)",
                                                  r"(?=.*\bmy\b)(?=.*\bbirthday\b)",
                                                  r"(?=.*(\bsmart\b|\bintelligent\b|\bbrain\b))(?=.*\byour?\b)",
                                                  r"(?=.*(\blatest\b|\brecent\b))(?=.*\bpapers?\b)"],
                                                 [is_it_a_birthday,
                                                  start_whinetime_workflow,
                                                  any_new_publications,
                                                  reply_happy_birthday,
                                                  reply_closest_birthday,
                                                  list_birthdays,
                                                  my_birthday,
                                                  reply_brain_size,
                                                  reply_recent_papers],
                                                 [True, True, True, False, False, False, False, False, False],
                                                 [False, False, False, True, True, True, True, True, True]):
        replied = mention_action(message=message, regex=regex, action=action,
                                 case_sensitive=case, pass_message=pass_message, direct_msg=direct_msg)

        # return immediately if you match one
        if replied:
            return

    # send a catch-all message if nothing matches
    thread_ts = None if direct_msg else body["event"]["ts"]
    say(text=(f"{insert_british_consternation()} Okay, good news: I heard you. Bad news: I'm not a very "
              "smart bot so I don't know what you want from me :shrug::baby::gerald-deceased:"),
        thread_ts=thread_ts, channel=body["event"]["channel"])


def mention_action(message, regex, action, case_sensitive=False, pass_message=True, direct_msg=False):
    """Perform an action based on a message that mentions Gerald if it matches a regular expression

    Parameters
    ----------
    message : `Slack Message`
        Object containing slack message
    regex : `str`
        Regular expression against which to match. https://regex101.com/r/m8lFAb/1 is a good resource for
        designing these.
    action : `function`
        Function to call if the expression is matched
    case_sensitive : `bool`, optional
        Whether the regex should be case sensitive, by default False
    pass_message : `bool`, optional
        Whether to pass the message the object to the action function, by default True
    direct_msg : `bool`, optional
        Whether the message was a direct message (and thus whether to use a thread), by default False

    Returns
    -------
    match : `bool`
        Whether the regex was matched
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    if re.search(regex, message["text"], flags=flags):
        if pass_message:
            action(message, direct_msg=direct_msg)
        else:
            action()
        return True
    else:
        return False


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
    matched = False

    # move it all to lower case if you don't care
    if not case_sensitive:
        message = message.lower()

    # go through each potential trigger
    for trigger in triggers:
        # if you find it in the message
        if message.find(trigger) >= 0:
            matched = True

            # if the response is a list then pick a random one
            if isinstance(response, list):
                response = np.random.choice(response)

            # send a message and break out
            app.client.chat_postMessage(channel=ch_id, text=response, thread_ts=thread_ts)
            break
    return matched


""" ---------- EMOJI HANDLING ---------- """


@app.event("emoji_changed")
def new_emoji(body, say):
    if body["event"]["subtype"] == "add":
        emoji_add_messages = ["I'd love to know the backstory on that one :eyes:",
                              "Anyone want to explain this?? :face_with_raised_eyebrow:",
                              "Feel free to put it to use on this message",
                              "Looks like I've found my new favourite :gerald-love:",
                              "And that's all the context you're getting :shushing_face:"]
        rand_msg = emoji_add_messages[np.random.randint(len(emoji_add_messages))]

        ch_id = find_channel("random")
        say(f'Someone just added :{body["event"]["name"]}: - {rand_msg}', channel=ch_id)


""" ---------- WHINETIME ---------- """


@app.view("whinetime-modal")
def whinetime_submit(ack, body, client, logger):
    # acknowledge the submission
    ack()

    global latest_whinetime_message
    if latest_whinetime_message is not None:
        app.client.chat_delete(channel=latest_whinetime_message["channel"],
                               ts=latest_whinetime_message["ts"])
        latest_whinetime_message = None

    # find the host
    host = None
    for block in body["view"]["blocks"]:
        if block["block_id"] == "whinetime-host-str":
            host = block["text"]["text"].split("@")[-1].split(">")[0]

    # get the values from the form
    state = body["view"]["state"]["values"]
    location = state["whinetime-location"]["whinetime-location"]["value"]
    date = state["whinetime-date"]["datepicker-action"]["selected_date"]
    time = state["whinetime-time"]["timepicker-action"]["selected_time"]

    ch_id = find_channel("whinetime")

    # convert the information to a datetime object
    year, month, day = list(map(int, date.split("-")))
    hour, minute = list(map(int, time.split(":")))
    dt = datetime.datetime(year, month, day, hour, minute)

    # format it nicely
    formatted_date = custom_strftime("%A (%B {S}) at %I:%M%p", dt)

    # send out an initial message to tell people the plan and ask for reactions
    message = app.client.chat_postMessage(text=(f"Okay folks, we're good to go (thanks to <@{host}> for "
                                                "hosting)! Whinetime will happen on "
                                                f"*{formatted_date}* at *{location}*. I'll remind you closer "
                                                "to the time but now react to this message with :beers: if "
                                                "you're coming!"), channel=ch_id)
    # start the reactions going
    app.client.reactions_add(channel=ch_id, timestamp=message["ts"], name="beers")

    # calculate some timestamps in the future (I hope)
    day_before = (dt - datetime.timedelta(days=1)).strftime("%s")
    hour_before = (dt - datetime.timedelta(hours=1)).strftime("%s")

    # attempt to send reminders (using Try because people may be too close to the time)
    try:
        result = client.chat_scheduleMessage(
            channel=ch_id,
            text=("Only one day to go until #whinetime! :wine_glass: Don't forget to react to the message "
                  "above if you're coming"),
            post_at=day_before
        )
        logger.info(result)

    except SlackApiError as e:
        logger.error("Error scheduling message: {}".format(e))

    try:
        result = client.chat_scheduleMessage(
            channel=ch_id,
            text=("Feeling that Friday afternoon fatigue? You need some #whinetime mate and luckily it's "
                  f"only one hour to go :meowparty::meowparty: Remember it's at {location} this week, "
                  "hope you guys have fun, bring a souvenir for me! :gerald-wave:"),
            post_at=hour_before
        )
        logger.info(result)

    except SlackApiError as e:
        logger.error("Error scheduling message: {}".format(e))


@app.action("whinetime-open")
def whinetime_logistics(body, client):
    # open the modal when someone clicks the button
    host = body["actions"][0]["value"]
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
            "emoji": True,
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
                "block_id": "whinetime-host-str",
                "text": {
                    "type": "mrkdwn",
                    "text": (f"Okay you're the boss <@{host}>, what's the plan? Let me know and I'll send "
                             "reminders out for whinetime!")
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
                    "initial_date": f"{datetime.date.today().strftime(r'%Y-%m-%d')}",
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
    ch_id = find_channel("whinetime")

    # get all of the members in the channel
    members = app.client.conversations_members(channel=ch_id)["members"]

    # choose someone random (but NOT Gerald lol)
    members = list(set(members) - set([GERALD_ID]) - set(not_these))
    if members == []:
        app.client.chat_postMessage(text=(f"{insert_british_consternation()} I've tried everyone in the "
                                          "channel and it seems no one is free to host! "
                                          ":smiling_face_with_tear:"), channel=ch_id)
        return

    random_member = np.random.choice(members)
    not_these.append(random_member)

    if not reroll:
        app.client.chat_postMessage(text=("Dumroll please :drum_with_drumsticks:...it's time to pick a "
                                          "whinetime host"), channel=ch_id)
    else:
        messages = [("Not whinetime eh? Are you sure? You could be great, you know, whinetime will help you "
                     "on the way to greatness, no doubt about that — no? Well, if you're sure — better "
                     f"be ~GRYFFINDOR~ <@{random_member}>! :mage:"),
                    "Okay let's try that again, your whinetime host will be...:drum_with_drumsticks:",
                    "Nevermind, let's choose someone else, how about...:drum_with_drumsticks:",
                    ("Not to worry anonymous citizen, the mantle will be passed on "
                     "to...:drum_with_drumsticks:"),
                    "Go go whinetime host choosing...:drum_with_drumsticks:"]
        app.client.chat_postMessage(text=np.random.choice(messages).replace("\n", " "), channel=ch_id)

    # post the announcement
    announcement = app.client.chat_postMessage(channel=ch_id, blocks=[
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
                    "value": random_member,
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
    global latest_whinetime_message
    latest_whinetime_message = announcement


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
    app.client.chat_postMessage(channel=find_channel("random"),
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
    with open("data/grad_info.csv") as birthday_file:
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


def list_birthdays(message, direct_msg=False):
    """List everyone's birthdays in a message in reply to someone

    Parameters
    ----------
    message : `Slack message`
        A slack message object
    direct_msg : `bool`, optional
        Whether the message was a direct message (and thus whether to use a thread), by default False
    """
    # get all of the birthdays
    info = get_all_birthdays()

    # two separate lists of whether we know the birthday or not
    unknowns = ""
    knowns = ""

    # add names to the correct list
    for name, birthday in info:
        if birthday is None:
            unknowns += f"• {name}\n"
        else:
            knowns += f"• {name} - {birthday}\n"

    # combine into a full list message
    birthday_list = ":birthday: Here's a list of birthdays that I know\n" + knowns
    birthday_list += "\n:question: And here's a list of people I know but whose birthdays I don't\n" + unknowns

    # post the message as a reply
    thread_ts = None if direct_msg else message["ts"]
    app.client.chat_postMessage(text=birthday_list.rstrip(), channel=message["channel"],
                                thread_ts=thread_ts)


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

                    # do something special if it is Gerald's birthday
                    if person == "gerald":
                        gif_url = ("https://raw.githubusercontent.com/TomWagg/gerald/main/img"
                                   "/birthday_gifs/gerald.gif")

                        # post the message with the GIF
                        app.client.chat_postMessage(channel=find_channel("random"),
                                                    text=":birthday: A special birthday :birthday:",
                                                    blocks=[
                                                        {
                                                            "type": "section",
                                                            "text": {
                                                                "type": "mrkdwn",
                                                                "text": ("Hey psst, I'm sure you've got a "
                                                                         "surprise party in the works but "
                                                                         "just in case you forgot..."),
                                                            }
                                                        },
                                                        {
                                                            "type": "image",
                                                            "image_url": gif_url,
                                                            "alt_text": "birthday"
                                                        }
                                                    ])
                    else:
                        say_happy_birthday(user["id"])
    else:
        print("No birthdays today!")


def closest_birthday():
    """ Work out when the closest birthday to today is """
    today = datetime.date.today()

    usernames = []
    names = []
    closest_time = np.inf

    # go through the birthday list
    with open("data/grad_info.csv") as birthdays:
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


def reply_closest_birthday(message, direct_msg=False):
    """Reply to someone with the next closest birthday to today

    Parameters
    ----------
    message : `Slack message`
        A slack message object
    direct_msg : `bool`, optional
        Whether the message was a direct message (and thus whether to use a thread), by default False
    """
    # get the closest birthday
    _, names, closest_time = closest_birthday()

    # write a string for how close it is (and be dramatic if it is today)
    time_until_str = f"it's in {closest_time} days!" if closest_time != 0 else "it's today :scream:!!"

    # if it is just one birthday
    thread_ts = None if direct_msg else message["ts"]
    if len(names) == 1:
        reply = f"The next person to have a birthday is {names[0]} and "
        reply += time_until_str
        app.client.chat_postMessage(text=reply, channel=message["channel"], thread_ts=thread_ts)
    else:
        reply = "The next people to have birthdays are " + " AND ".join(names) + " and "
        reply += time_until_str
        app.client.chat_postMessage(text=reply, channel=message["channel"], thread_ts=thread_ts)


def reply_happy_birthday(message, direct_msg=False):
    """Reply to someone if they wish Gerald a happy birthday

    Parameters
    ----------
    message : `Slack message`
        A slack message object
    direct_msg : `bool`, optional
        Whether the message was a direct message (and thus whether to use a thread), by default False
    """
    thread_ts = None if direct_msg else message["ts"]
    today = datetime.date.today()
    if today.month == 8 and today.day == 5:
        app.client.chat_postMessage(text="Thank you!! That's so nice of you to remember :gerald-love:",
                                    channel=message["channel"], thread_ts=thread_ts)
    else:
        app.client.chat_postMessage(text=("Oh um, well thank you, I do appreciate the sentiment...but my "
                                          "birthday is actually on the 5th of August "
                                          ":face_with_rolling_eyes:"),
                                    channel=message["channel"], thread_ts=thread_ts)


def my_birthday(message, direct_msg=False):
    users = app.client.users_list()["members"]
    my_username = None
    for user in users:
        if user["id"] == message["user"]:
            my_username = user["name"]

    thread_ts = None if direct_msg else message["ts"]
    with open("data/grad_info.csv") as birthday_file:
        for grad in birthday_file:
            _, username, _, birthday, _ = grad.split(",")
            if username == my_username:
                if birthday == "-":
                    app.client.chat_postMessage(text=(f"{insert_british_consternation()} This is a little "
                                                      "awkward but...I don't know your "
                                                      "birthday :sweat_smile:. I did my research using the "
                                                      "Grad Wiki and got them from <https://github.com/UW-Astro-Grads/GradWiki/wiki/Community%3APhone-List|this page>. "
                                                      "If you could add your birthday there and then let "
                                                      f"{GERALD_ADMIN} know I'll be sure to remember it "
                                                      "I promise!!"),
                                                channel=message["channel"], thread_ts=thread_ts)
                else:
                    day, month = map(int, birthday.split("/"))
                    dt = datetime.date(day=day, month=month, year=2022)
                    app.client.chat_postMessage(text=("I know your birthday! :gerald-search: "
                                                      f"It's {custom_strftime('%B {S}', dt)}"),
                                                channel=message["channel"], thread_ts=thread_ts)


""" ---------- PUBLICATION ANNOUNCEMENTS ---------- """


def reply_recent_papers(message, direct_msg=False):
    """Reply to a message with the most recent papers associated with a particular user or ORCID ID

    Parameters
    ----------
    message : `Slack Message`
        A slack message object
    direct_msg : `bool`, optional
        Whether the message was a direct message (and thus whether to use a thread), by default False
    """
    # search for ORCID IDs in the message
    orcids = re.findall(r"\d{4}-\d{4}-\d{4}-\d{4}", message["text"])
    names = []
    direct_orcids = True

    thread_ts = None if direct_msg else message["ts"]

    numbers = re.findall(r" \d* ", message["text"])
    n_papers = 1 if len(numbers) == 0 else int(numbers[0])

    # if don't find any then look for users instead
    if len(orcids) == 0:
        direct_orcids = False
        # find any tags
        tags = re.findall(r"<[^>]*>", message["text"])

        # remove Gerald from the tags
        if f"<@{GERALD_ID}>" in tags:
            tags.remove(f"<@{GERALD_ID}>")

        # let people say "my" paper
        if len(tags) == 0 and message["text"].find("my") >= 0:
            tags.append(f"<@{message['user']}>")

        # if you found at least one tag
        if len(tags) > 0:
            # go through each of them
            for tag in tags:
                # convert the tag to an orcid and a name
                orcid, name = get_orcid_name_from_user_id(tag.replace("<@", "").replace(">", ""))

                # if we don't know this person's ORCID then crash out with a message
                if orcid is None:
                    app.client.chat_postMessage(text=(f"{insert_british_consternation()} I think you asked "
                                                      f"for most recent papers but I don't know {tag}'s "
                                                      "ORCID ID sorry :persevere:. You can add it to "
                                                      "<https://github.com/UW-Astro-Grads/GradWiki/wiki/Community%3APhone-List|the list> in the wiki though! :slightly_smiling_face:"),
                                                channel=message["channel"], thread_ts=thread_ts)
                    return
                else:
                    # otherwise just append info
                    orcids.append(orcid)
                    names.append(name)

    # if we found no orcids through all of that then crash out with a message
    if len(orcids) == 0:
        app.client.chat_postMessage(text=(f"{insert_british_consternation()} I think you asked for some "
                                          "recent papers but I couldn't find any ORCID IDs or user tags in "
                                          "the message sorry :pleading_face:"),
                                    channel=message["channel"], thread_ts=thread_ts)
        return

    # go through each orcid
    for i in range(len(orcids)):
        # get the most recent n papers
        papers, times = get_n_most_recent_papers(orcids[i], n=n_papers)
        if papers is None or times is None:
            app.client.chat_postMessage(text=("Terribly sorry old chap but it seems that there's a problem "
                                              f"with that ORCID ID ({orcids[i]}) :hmmmmm:. Either the ID is "
                                              "invalid _or_ the owner has not linked it to their arXiv "
                                              "account. Encourage them to do so through "
                                              "<https://arxiv.org/help/orcid|this link>!"),
                                        channel=message["channel"], thread_ts=thread_ts)
            return

        # if it is just one paper then give lots of details
        if n_papers == 1:
            paper, time = papers[0], times[0]

            # create a brief message for before the paper
            preface = f"The most recent paper from {orcids[i]} was published on the arXiv {time} days ago"
            authors = f"_Authors: {paper['authors']}_"

            # if you supplied tags (so we know their name)
            if not direct_orcids:
                # use the tag in the pre-message
                preface = f"The most recent paper from {tags[i]} was published on the arXiv {time} days ago"

                # create an author list, adding each but BOLDING the author that matches the orcid
                authors = bold_grad_author(paper['authors'], names[i])

            # format the date nicely
            date_formatted = custom_strftime("%B {S} %Y", paper['date'])

            # send the pre-message then a big one with the paper info
            app.client.chat_postMessage(text=preface, channel=message["channel"], thread_ts=thread_ts)
            app.client.chat_postMessage(text=preface, blocks=[
                                            {
                                                "type": "section",
                                                "text": {
                                                    "type": "mrkdwn",
                                                    "text": f"*{paper['title']}*"
                                                }
                                            },
                                            {
                                                "type": "section",
                                                "text": {
                                                    "type": "mrkdwn",
                                                    "text": authors
                                                }
                                            },
                                            {
                                                "type": "section",
                                                "fields": [
                                                    {
                                                        "type": "mrkdwn",
                                                        "text": f"_Date: {date_formatted}_"
                                                    },
                                                    {
                                                        "type": "mrkdwn",
                                                        "text": f"<{paper['link']}|arXiv link>"
                                                    }
                                                ]
                                            },
                                            {
                                                "type": "section",
                                                "text": {
                                                    "type": "mrkdwn",
                                                    "text": f"Abstract: {paper['abstract']}"
                                                }
                                            }
                                        ],
                                        channel=message["channel"], thread_ts=thread_ts)
        else:
            # if it's multiple papers then give a condensed list
            blocks = [
                [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (f"<{paper['link']}|*{paper['title']}*> - "
                                     f"_{paper['authors'].split(',')[0].split(' ')[-1]} "
                                     f"et al. ({paper['date'].year})_")
                        }
                    }
                ] for paper in papers
            ]
            blocks = list(np.ravel(blocks))

            # join up the times with commas and a final "and"
            time_str = ", ".join([str(time) for time in times[:-1]])
            time_str = time_str.rstrip() + f" and {times[-1]}"

            # same preface stuff as above but with many papers
            preface = (f"The most {n_papers} recent papers from {orcids[i]} were published on the arXiv "
                       f"{time_str} days ago respectively. Here are the titles and links:")

            # if you supplied tags (so we know their name)
            if not direct_orcids:
                # use the tag in the pre-message
                preface = (f"The most {n_papers} recent papers from {tags[i]} were published on the arXiv "
                           f"{time_str} days ago respectively. Here are the titles and links:")

            # post the messages
            app.client.chat_postMessage(text=preface, channel=message["channel"], thread_ts=thread_ts)
            app.client.chat_postMessage(text=preface, blocks=blocks,
                                        channel=message["channel"], thread_ts=thread_ts, unfurl_links=False)


def get_orcid_name_from_user_id(user_id):
    """Convert a user ID to an ORCID ID and name

    Parameters
    ----------
    user_id : `str`
        Slack ID of a user

    Returns
    -------
    orcid : `str`
        ORCID ID

    name : `str`
        Person's full name
    """
    # get the full list of slack users
    users = app.client.users_list()["members"]

    # find the matching username for the ID
    orcid_username = None
    for user in users:
        if user["id"] == user_id:
            orcid_username = user["name"]
            break

    # go through the grad info file
    with open("data/grad_info.csv") as orcid_file:
        for grad in orcid_file:
            if grad[0] == "#":
                continue
            name, username, _, _, orcid = grad.split(",")

            # find the matching username and return the info (if it exists)
            if username == orcid_username:
                if orcid == "-":
                    return None, name
                else:
                    return orcid.rstrip(), name

    # return None if can't find them in the table
    return None, None


def any_new_publications():
    """ Check whether any new publications by grad students are out """
    no_new_papers = True

    # go through the file of grads
    with open("data/grad_info.csv") as grad_file:
        for grad in grad_file:
            # skip any comments
            if grad[0] == "#":
                continue

            name, username, _, _, orcid = grad.split(",")
            orcid = orcid.rstrip()

            # skip anyone who doesn't have an orcid ID
            if orcid == "-":
                continue

            # get the latest 3 papers from this person (I'm assuming no one will publish more than 3 a day!)
            papers, times = get_n_most_recent_papers(orcid, 3)

            # skip anyone who has a bad ORCID ID
            if papers is None or times is None:
                continue

            # get any papers that were published today
            today_papers = []
            for paper, time in zip(papers, times):
                if time == 0:
                    today_papers.append(paper)

            # if this person has one then announce it!
            if len(today_papers) > 0:
                no_new_papers = False
                announce_publication(username, name, today_papers)

    if no_new_papers:
        print("No new papers!")


def announce_publication(username, name, papers):
    """Announce to the workspace that someone has published a new paper(s)

    Parameters
    ----------
    username : `str`
        Slack username of the person
    name : `str`
        Plain name of the person
    papers : `list` of `dicts`
        List of dictionaries of the papers (I imagine usually just one but just in case)
    """
    # find the user ID of the person
    users = app.client.users_list()["members"]
    user_id = None
    for user in users:
        if user["name"] == username:
            user_id = user["id"]
            break

    if user_id is None:
        return

    # choose an randon adjective
    adjective = np.random.choice(["Splendid", "Tremendous", "Brilliant",
                                  "Excellent", "Fantastic", "Spectacular"])

    # if it's just one then write some messages to them
    if len(papers) == 1:
        preface = f"Look what I found on the arXiv this morning :tada: {adjective} work <@{user_id}> :clap:"
        outro = ("I put the abstract in the thread for anyone interested in learning more "
                 f"- again, a big congratulations to <@{user_id}> for this awesome paper")
    else:
        # edit the messages if there is more than one paper
        preface = (f"Look what I found on the arXiv this morning :tada: Not 1 but {len(papers)} new papers "
                   f"from <@{user_id}>!! :clap::scream:")
        outro = ("I put the abstracts in the thread for anyone interested in learning more "
                 f"- again, a big congratulations to <@{user_id}> for these awesome papers")

    # add the same starting blocks for all
    start_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":rotating_light: New grad paper alert!! :rotating_light:",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": preface
            }
        },
    ]

    # add some blocks for each paper
    paper_blocks = []
    for paper in papers:
        paper_blocks.extend(
            [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"<{paper['link']}|*{paper['title']}*>"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": bold_grad_author(paper["authors"], name)
                    }
                }
            ])

    # add a single end block about the abstract
    end_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": outro
            }
        }
    ]

    # combine all of the blocks
    blocks = start_blocks + paper_blocks + end_blocks

    # create blocks for each abstract
    abstract_blocks = [
        [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": paper['abstract']
                }
            }
        ] for paper in papers
    ]

    # flatten out the blocks into the right format
    blocks = list(np.ravel(blocks))
    abstract_blocks = list(np.ravel(abstract_blocks))

    # find the channel and send the initial message
    channel = find_channel("bot-test")
    message = app.client.chat_postMessage(text="Congrats on your new paper(s)!",
                                          blocks=blocks, channel=channel, unfurl_links=False)

    # reply in thread with the abstracts
    app.client.chat_postMessage(text="Your paper abstracts:", blocks=abstract_blocks,
                                channel=channel, thread_ts=message["ts"])


""" ---------- HELPER FUNCTIONS ---------- """


def bonk_someone(message):
    # find the user to bonk
    bonkers = re.search("\<(.*?)\>", message["text"])

    # if there is one then BONK them
    if bonkers is not None:
        person_to_bonk = bonkers[0]

        followups = ["Now go and think about what you've done! :gerald-angry:",
                     "Bad grad student, I'll take away your :coffee:!",
                     "You're lucky Asimov made that first law mate...:robot_face::skull:",
                     "There's more where that came from"]
        followup = np.random.choice(followups)

        app.client.chat_postMessage(text=f"BONK {person_to_bonk} :bonk::bonk:\n" + followup,
                                    thread_ts=message["ts"], channel=message["channel"])
    else:
        app.client.chat_postMessage(text=(f"{insert_british_consternation()} I couldn't work out who "
                                          "to bonk :sob:"),
                                    thread_ts=message["ts"], channel=message["channel"])


def reply_brain_size(message, direct_msg=False):
    """Reply to a message with Gerald's current brain size

    Parameters
    ----------
    message : `Slack Message`
        A slack message object
    direct_msg : `bool`, optional
        Whether the message was a direct message (and thus whether to use a thread), by default False
    """
    # count the number of lines of code in Gerald's brain
    brain_size = 0
    for file in os.listdir("."):
        if file.endswith(".py"):
            with open(os.path.join(".", file)) as brain_bit:
                brain_size += len(brain_bit.readlines())

    # tell whoever asked
    responses = [(f"Well my brain is {brain_size} lines of code long, so don't worry, it'll probably be a "
                  "couple of years until I'm intelligent enough to replace you :gerald-wink:"),
                 (f"Given that my brain is already {brain_size} lines of code long and the rate at which it's"
                  f" growing, it'll probably be around {np.random.randint(2, 10)} years until I am able to "
                  "~take over from you pesky humans~ help you even better! :innocent: :gerald-learning:"),
                 (f"I'm clocking a reasonable {brain_size} lines of code in my brain these days, which "
                  "unfortunately means I'm now over-qualified for reality TV :zany_face:"),
                 (f"I'm still learning but my brain is already {brain_size} lines of "
                  "code long! :brain::gerald-learning:")]

    thread_ts = None if direct_msg else message["ts"]
    app.client.chat_postMessage(text=np.random.choice(responses),
                                channel=message["channel"], thread_ts=thread_ts)


def insert_british_consternation():
    choices = ["Oh fiddlesticks!", "Ah burnt crumpets!", "Oops, I've bangers and mashed it!",
               "It seems I've had a mare!", "It appears I've had a mare!",
               "Everything is very much not tickety-boo!", "Oh dearie me!",
               "My profuse apologies but we've got a problem!",
               "I haven't the foggiest idea what just happened!",
               ("Oh dear, one of my servers just imploded so that can't be a terribly positive "
                "sign :exploding_head:"),
               "Ouch! Did you know errors hurt me? :smiling_face_with_tear:"]
    return np.random.choice(choices)


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
    return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')


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
    any_new_publications()


# start Gerald
if __name__ == "__main__":
    scheduler = BackgroundScheduler({'apscheduler.timezone': 'US/Pacific'})
    scheduler.add_job(every_morning, "cron", hour=9, minute=32)
    scheduler.start()
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()

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


def suffix(d):
    return 'th' if 11 <= d <= 13 else {1: 'st',2: 'nd',3: 'rd'}.get(d % 10, 'th')


def custom_strftime(format, t):
    return t.strftime(format).replace('{S}', str(t.day) + suffix(t.day))

# Listens to incoming messages that contain "hello"
@app.message("hello")
def message_hello(message, say):
    # say() sends a message to the channel where the event was triggered
    say(
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Hey there <@{message['user']}>!"},
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Click Me"},
                    "action_id": "button_click"
                }
            }
        ],
        text=f"Hey there <@{message['user']}>!",
        thread_fs=message["ts"]
    )


@app.action("button_click")
def action_button_click(body, ack, say):
    # Acknowledge the action
    ack()
    say(f"<@{body['user']['id']}> clicked the button", thread_ts=body["event"]["ts"])


# Listens to incoming messages that contain "hello"
# To learn available listener arguments,
# visit https://slack.dev/bolt-python/api-docs/slack_bolt/kwargs_injection/args.html
@app.message("test")
def message_test(message, say):
    # say() sends a message to the channel where the event was triggered
    say(f"<@{message['user']}> look I can use emojis too :bonk: :tom-approves:", thread_ts=message["ts"])
    print(message)


@app.message(re.compile("(bonk|Bonk|BONK)"))
def bonk_someone(message, say):
    print(message)
    bonkers = re.search("\<(.*?)\>", message["text"])
    if bonkers is not None:
        person_to_bonk = bonkers[0]
    say(f"BONK {person_to_bonk} :bonk::bonk:", thread_ts=message["ts"])


@app.message(re.compile("(tom|Tom)"))
def react_with_tom(message, client):
    client.reactions_add(
        channel=message["channel"],
        timestamp=message["ts"],
        name="tom"
    )


@app.message("undergrad|Undergrad")
def no_undergrads(message, client):
    client.reactions_add(
        channel=message["channel"],
        timestamp=message["ts"],
        name="underage"
    )


@app.message("gerald|Gerald")
def gerald(message, client):
    client.reactions_add(
        channel=message["channel"],
        timestamp=message["ts"],
        name="gerald"
    )
    client.reactions_add(
        channel=message["channel"],
        timestamp=message["ts"],
        name="eyes"
    )


@app.event("message")
def handle_message_events(body, logger):
    print("I detected a message", body)
    logger.info(body)


@app.view("whinetime-modal")
def whinetime_submit(ack, body, say, client, logger):
    ack()
    state = body["view"]["state"]["values"]
    location = state["whinetime-location"]["whinetime-location"]["value"]
    date = state["whinetime-date"]["datepicker-action"]["selected_date"]
    time = state["whinetime-time"]["timepicker-action"]["selected_time"]

    channels = client.conversations_list(exclude_archived=True)
    ch_id = None
    for channel in channels["channels"]:
        if channel["name"] == "bot-test":
            ch_id = channel["id"]
            break

    if ch_id is None:
        return

    year, month, day = list(map(int, date.split("-")))
    hour, minute = list(map(int, time.split(":")))
    dt = datetime.datetime(year, month, day, hour, minute)

    formatted_date = custom_strftime("%A (%B {S}) at %I:%M%p", dt)

    say(f"Okay folks, we're good to go! Whinetime will happen on {formatted_date} at {location}. I'll remind you closer to the time but now react to this message with :beers: if you're coming!", channel=ch_id)

    # calculate some timestamps in the future (I hope)
    day_before = (dt - datetime.timedelta(days=1)).strftime("%s")
    hour_before = (dt - datetime.timedelta(hours=1)).strftime("%s")

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
                    "text": f"Whinetime ({datetime.datetime.now().strftime('%d/%m/%y')})",
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


@app.event("app_mention")
def reply_to_mentions(say, body, client):
    no_matches = True

    status_checkers = ["status", "okay", "ok"]
    for match in status_checkers:
        if body["event"]["text"].find(match) >= 0:
            no_matches = False
            say("Don't worry, I'm okay. In fact, I'm feeling positively tremendous old bean!",
                thread_ts=body["event"]["ts"])
            break

    thanks = ["thank", "Thank", "THANK"]
    for thank in thanks:
        if body["event"]["text"].find(thank) >= 0:
            no_matches = False
            responses = ["You're welcome!", "My pleasure!", "Happy to help!"]
            say(np.random.choice(responses), thread_ts=body["event"]["ts"])
            break

    if body["event"]["text"].find("whinetime") >= 0:
        no_matches = False
        channels = client.conversations_list(exclude_archived=True)
        ch_id = None
        for channel in channels["channels"]:
            if channel["name"] == "bot-test":
                ch_id = channel["id"]
                break

        if ch_id is None:
            return

        members = client.conversations_members(channel=ch_id)["members"]
        random_member = np.random.choice(members)
        while random_member == GERALD_ID:
            random_member = np.random.choice(members)

        say("Dumroll please :drum_with_drumsticks:...it's time to pick a whinetime host", channel=ch_id)

        say(blocks=[
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Whinetime ({datetime.datetime.now().strftime('%d/%m/%y')})",
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
                        "value": "none",
                        "action_id": "whinetime-re-roll"
                    }
                ]
            },
        ])

    if no_matches:
        say("Okay, good news: I heard you, bad news: I'm not a very smart bot so I don't know what you want from me :shrug::baby::robot_face:",
            thread_ts=body["event"]["ts"])


@app.event("emoji_changed")
def new_emoji(body, say):
    if body["event"]["subtype"] == "add":
        emoji_add_messages = ["I'd love to know the backstory on that one",
                              "Anyone want to explain this??",
                              "Feel free to put it to use on this message",
                              "Looks like I've found my new favourite",
                              "And that's all the context you're getting"]
        rand_msg = emoji_add_messages[np.random.randint(len(emoji_add_messages))]
        say(f'Someone just added :{body["event"]["name"]}: - {rand_msg}', channel="C03S53SC1FZ")


def scheduled_function():
    print("Test test test")


# scheduler = BackgroundScheduler({'apscheduler.timezone': 'UTC'})
# scheduler.add_job(my_scheduled_job, "cron", day_of_week="mon", hour=16, minute=0)
# scheduler.start()

scheduler = BackgroundScheduler({'apscheduler.timezone': 'US/Pacific'})
scheduler.add_job(scheduled_function, "cron", day_of_week="sat", hour=10, minute=25)
# scheduler.add_job(scheduled_function, "interval", seconds=5)


# start Gerald
if __name__ == "__main__":
    scheduler.start()
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()

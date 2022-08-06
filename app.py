import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import re
import numpy as np

# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))


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


@app.event("message")
def handle_message_events(body, logger):
    print("I detected a message", body)
    logger.info(body)


@app.event("app_mention")
def reply_to_mentions(say, body):
    no_matches = True

    status_checkers = ["status", "okay", "ok"]
    for match in status_checkers:
        if body["event"]["text"].find(match) > 0:
            no_matches = False
            say("Don't worry, I'm okay. In fact, I'm feeling positively tremendous old bean!",
                thread_ts=body["event"]["ts"])
            break

    if no_matches:
        say("Okay I heard you, but I'm also not a very smart bot so I don't know what you want from me",
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


# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()

import os
from waveshare import epd2in13_V3
from PIL import Image, ImageDraw, ImageFont

import os.path
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import datetime
import pytz

font24 = ImageFont.truetype('waveshare/Font.ttc', 24)

epd = epd2in13_V3.EPD()
epd.init()
epd.Clear(0xFF)

# Set the timezone to your local timezone
tz = pytz.timezone('America/Toronto')
# Fixed port is needed when whitelisting redirect url on Google cloud
# Make sure this port is already open
PORT = 8999
# The calendar ID of the calendar you want to monitor
# If you want to monitor your own Google calendar, set this to 'primary'
calendarID = 'primary'
updateInterval = 600  # 10 minutes

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def fetch_calendar_events():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=PORT)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    now = datetime.datetime.now(tz)
    ten_minutes_ago = (now - datetime.timedelta(minutes=10)).isoformat()
    today_evening = now.replace(hour=20, minute=0, second=0, microsecond=0).isoformat()

    events_result = service.events().list(calendarId=calendarID, timeMin=ten_minutes_ago,
                                          timeMax=today_evening,
                                          maxResults=4, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    return events


def format_events(events):
    formatted_events = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        summary = event.get('summary', 'No Title')

        start_time = datetime.datetime.fromisoformat(start).strftime('%H:%M')
        end_time = datetime.datetime.fromisoformat(end).strftime('%H:%M')

        formatted_events.append(f"{start_time} => {end_time} [{summary}]")
        # Sometimes you don't have access to the shared calendars events names:
        # formatted_events.append(f"{start_time} => {end_time}")
    return formatted_events


def monitor_calendar_events():
    last_events = None

    while True:
        current_events = fetch_calendar_events()
        formatted_events = format_events(current_events)

        if formatted_events != last_events:
            draw_texts(formatted_events)
            last_events = formatted_events

        time.sleep(updateInterval)  # Wait for 10 minutes


def draw_texts(texts):
    image = Image.new('1', (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)
    for i, text in enumerate(texts):
        draw.text((1, 1 + i * 30), text, font=font24, fill=0)  # [1,1] is the top left corner of the text
    epd.display(epd.getbuffer(image))


if __name__ == '__main__':
    monitor_calendar_events()

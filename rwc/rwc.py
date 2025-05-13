'''
2023
'''
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import redis
import os
from flask import Flask, request, render_template, Response, abort, jsonify
import sys
import traceback
import json
from twilio.rest import Client
import time
from datetime import datetime, date, timedelta
import pytz
import uuid
import traceback
import socket

RWC_TIX_URL = 'https://tickets.rugbyworldcup.com/en'
RWC_TIX_LOGIN_URL = 'https://tickets.rugbyworldcup.com/en/user/login'

TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
REDIS_HOST = os.environ['REDIS_HOST']
REDIS_PW = os.environ['REDIS_PW']
REDIS_PORT = os.environ['REDIS_PORT']
HEADLESS = os.environ.get('HEADLESS')
REDIS_TTL = 60 * 60 * 48
GECKODRIVER_PATH = '../geckodriver'
LOG_FILE_NAME = 'geckodriver.log'
TIX_ID = os.environ['TIX_ID']
TIX_PW = os.environ['TIX_PW']

def send_sms(text):
    EST = pytz.timezone('US/Eastern')
    time_now = datetime.now(EST).strftime('%b %d - %H:%M:%S')
    msg = '%s:\n%s' % (time_now, text)
    message = twilio_client.messages.create(
        body=msg,
        from_='+19842144312',
        to='+19192446142'
    )
    return message.sid

def send_mms(media_url):
    message = twilio_client.messages.create(
        from_='+19842144312',
        to='+19192446142',
        media_url=media_url
    )
    return message.sid

def get_screen_cap(driver):
    now = datetime.now()
    filename = '/automation/%s.%s.png' % (now.strftime('%m-%d-%H.%M.%S'), uuid.uuid1())
    mms_url = 'https://automation-u4sp7ks5ea-uc.a.run.app/runtime_images%s' % filename
    print("Screen cap url: %s" % mms_url)
    image = driver.get_screenshot_as_png()
    redis_client.setex(filename, REDIS_TTL, image)
    
    return mms_url

def get_driver():
    options = FirefoxOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    if HEADLESS == 'True':
        log('Running headless')
        options.add_argument('--headless')
    else:
        log('Not running headless')
    service = FirefoxService(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(service=service, options=options)
    size = driver.get_window_size()
    driver.set_window_size(size['width'],size['height']*2)
    return driver

def log(msg):
    print('%s - %s' % (datetime.now().strftime('%m/%d/%y: %H:%M:%S'), msg))

def rwc():

    # TEAMS = [
    #     'New Zealand',
    #     'Portugal',
    #     'Romania',
    #     'Samoa',
    #     'Scotland',
    #     'South Africa',
    #     'Tonga',
    #     'Uruguay',
    #     'Wales'
    #     'Argentina',
    #     'Australia',
    #     'Chile',
    #     'England',
    #     'Fiji',
    #     'France',
    #     'Georgia',
    #     'Ireland',
    #     'Italy',
    #     'Japan',
    #     'Namibia'
    # ]

    TEAMS = [
        'England'
    ]

    MATCHES = [
        'Japan']

    def login(driver):
        driver.get(RWC_TIX_LOGIN_URL)
        # login_button = driver.find_element(By.CLASS_NAME, "user-account-login")
        # login_button.click()
        login_form = driver.find_element(By.ID, "user-login-form")
        id_field = login_form.find_element(By.ID, "edit-name")
        id_field.send_keys(TIX_ID)
        continue_button = login_form.find_element(By.ID, "edit-submit")
        continue_button.click()
        c2 = driver.find_elements(By.CLASS_NAME, "captcha")
        c2[0].click()
        print()

    def deal_with_cookie_prompt(driver):
        done = False
        attempt = 1
        while not done:
            try:
                button = driver.find_element(By.ID, "onetrust-accept-btn-handler")
                button.click()
                log('Dismissed cookie pompt.')
                done = True
            except Exception:
                log('Didn\'t see or couldn\'t dismuss cookie pompt.')
                time.sleep(1)
                attempt += 1
            if attempt > 5:
                raise Exception('Could not dismiss cookie prompt after %s attempts.' % attempt)
            else:
                time.sleep(1)

    def get_into_queue(driver):
        log('Loaded home page: %s.' % RWC_TIX_URL)
        time.sleep(1)
        log('Main ticketing page loaded')
        # Now deal with cookie prompt
        enter_buttons = driver.find_elements(By.CLASS_NAME, "btn-primary")
        if len(enter_buttons) == 1 and 'ENTER' in enter_buttons[0].text:
            enter_buttons[0].click()
        log('Clicked to enter queue.')
        time.sleep(1)
    

    def get_past_queue(driver):
        max_attempts = 40
        delay = 30 
        current_attempt = 1
        done = False
        through_queue = False
        muted = False
        while not done:
            buttons = driver.find_elements(By.ID, "onetrust-accept-btn-handler")
            if len(buttons) > 0:
                buttons[0].click()
                log('Through queue')
                done = True
                through_queue = True
            else:
                if current_attempt > max_attempts:
                    log('Not through queue after max attempts')
                    done = True
                else:
                    # Try this next. SPACE seems to mute video player. Try grabbing iframe and then pressing space.
                    # To work this seems to need focus to the player.
                    # Otherwise the code below then trys to click the mute button 
                    # if muted is False:
                    #     set_viewport_size(driver, 800, 600)
                    #     page = driver.find_element(By.TAG_NAME, "body")
                    #     print(page.rect)
                    #     print(page.location)
                    #     player = driver.find_element(By.TAG_NAME, "iframe")
                    #     print(player.rect)
                    #     print(player.location)
                    #     player.send_keys(Keys.SPACE)
                    #     p2 = driver.find_element(By.TAG_NAME, "iframe")
                    #     print(p2.rect)
                    #     print(p2.location)
                    #     print("Scroll height: %s" % driver.execute_script("return document.body.scrollHeight"))
                    #     driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    #     print("Viewport: %s" % driver.execute_script("return [window.innerWidth, window.innerHeight];"))
                    #     x_offset = 112
                    #     y_offset = player.rect['height'] - 20
                    #     ac = ActionChains(driver)
                    #     ac.move_to_element(player).move_by_offset(x_offset, y_offset).click().perform()


                    current_attempt += 1
                    percentages = driver.find_elements(By.CLASS_NAME, "percentage")
                    if len(percentages) > 0:
                        print(percentages[0])
                    log('In queue, waiting %s seconds' % delay)
                    time.sleep(delay)
        return through_queue

    def handle_queue(end_time, team):
        page = driver.find_element(By.TAG_NAME, "body")
        log("Put back in queue")
        timed_out = False
        while 'YOU ARE IN THE QUEUE' in page.text:
            time.sleep(10)
            page = driver.find_element(By.TAG_NAME, "body")
            if datetime.now() >= end_time:
                timed_out = True
                break
        if timed_out:
            log("Timed out in queue")
        else:
            log("Through queue")
            selects = driver.find_elements(By.CLASS_NAME, "js-team-filter")
            selects[0].send_keys(team)
            time.sleep(1)


    def match_match(offer, team):
        found = False
        if team in offer:
            for match in MATCHES:
                if match in offer:
                    found = True
                    break
        return found

    try:
        log(">>>> Attempt Start <<<<< ")
        start_time = datetime.now()
        driver = get_driver()
        driver.get(RWC_TIX_URL)
        get_into_queue(driver)
        # login(driver)
        # deal_with_cookie_prompt(driver)
        if get_past_queue(driver) is True:
            end_time = start_time + timedelta(minutes=5)
            while datetime.now() < end_time:
                time.sleep(1)
                done = False
                for team in TEAMS:
                    # First filter to just England games
                    selects = driver.find_elements(By.CLASS_NAME, "js-team-filter")
                    selects[0].send_keys(team)
                    time.sleep(1)
                    # Now loop through all offers looking for the matches we want
                    offers = driver.find_elements(By.CLASS_NAME, "list-ticket-content")
                    for i in range(0, len(offers)):
                        try:
                            offer = offers[i]
                            offer_text = offer.text[0:offer.text.find('\n')]
                            if match_match(offer_text, team):
                                log("Processing: %s" % offer_text)
                                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "js-show-offers")))
                                button = offer.find_element(By.CLASS_NAME, "actions-wrapper")   
                                button_text = button.text
                                if button_text != 'UNAVAILABLE':
                                    button.click()
                                    time.sleep(1)
                                    offer_modal = driver.find_element(By.CLASS_NAME, "modal-resale-option")
                                    offer_button = offer_modal.find_element(By.CLASS_NAME, "btn-resale")
                                    offer_button.click()
                                    time.sleep(1)

                                    ticket_contents = driver.find_elements(By.CLASS_NAME, "nb-tickets")
                                    if len(ticket_contents) > 0:
                                        log("Found tix for %s" % offer_text)
                                        ticket_text = ticket_contents[0].text
                                        if 'tickets' in ticket_text:
                                            offers = driver.find_elements(By.CLASS_NAME, "resale-pack-details")
                                            for offer in offers:
                                                offer.click()
                                                confirms = driver.find_elements(By.CLASS_NAME, "resale-listing-action")
                                                if len(confirms) > 0:
                                                    confirms[0].click()
                                                    time.sleep(20)
                                                    modals = driver.find_elements(By.CLASS_NAME, "ui-dialog")
                                                    if len(modals) > 0:
                                                        log("Tix not available")
                                                        #Dismiss modal with two enter keys
                                                        modals[0].send_keys(Keys.ESCAPE)
                                                        # modals[0].click()
                                                        # modals[0].send_keys(Keys.ESCAPE)
                                                        # modals[0].send_keys(Keys.RETURN)
                                                        # modals[0].send_keys(Keys.RETURN)
                                                        time.sleep(1)
                                                    else:
                                                        log("*** Tix available ***")
                                                        log("%s" % offer_text)
                                                        td = timedelta(minutes=20)
                                                        td2 = timedelta(seconds=20)
                                                        expires = datetime.now() + td - td2
                                                        expire_string = expires.strftime('%m/%d/%y: %H:%M:%S')
                                                        log("Cart expires: %s" % expire_string)
                                                        send_sms("%s\nCart expires:\n%s" % (offer_text, expire_string))
                                                        url = get_screen_cap(driver)
                                                        send_mms(url)
                                                        #Sleep during the expiration period of 20 min
                                                        time.sleep(20 * 60)
                                                        done = True
                                                        break
                                        else:
                                            log("Only 1 ticket found for %s." % offer_text)
                                    driver.back()
                                    log("Driver back from %s" % offer_text)
                                time.sleep(1)
                            if done is True:
                                break
                            else:
                                # Need to work by index and refresh the list of results because otherwise they get stale and
                                # result in exceptions
                                offers = driver.find_elements(By.CLASS_NAME, "list-ticket-content")
                        except Exception as e:
                            page = driver.find_element(By.TAG_NAME, "body")
                            if 'YOU ARE IN THE QUEUE' in page.text:
                                handle_queue(end_time, team)
                                offers = driver.find_elements(By.CLASS_NAME, "list-ticket-content")
                            else:
                                raise e

                    if done is True:
                        break

        log(">>>> Attempt End <<<<")
        driver.close()
    except Exception as e:
        log('Error: ' + str(e))
        traceback.print_exc()
        # get_screen_cap(driver)
        driver.close()
        raise e



account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
twilio_client = Client(account_sid, auth_token)
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PW)
rwc()

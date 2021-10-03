"""
2021
"""
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.options import Options as SafariOptions
from selenium.webdriver.chrome.options import Options as OperaOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
import redis
import os
from flask import Flask, request, render_template, Response, url_for, abort, send_file
import sys
import traceback
import json
from twilio.rest import Client
import time
from datetime import datetime, date
import uuid
import urllib.parse
import re

print('Just getting started...')
app = Flask(__name__)

@app.before_request
def do_something_whenever_a_request_comes_in():
    r = request
    url = r.url
    method = r.method
    print('>>>> Call into %s with %s ' % (url, method))
    # This is to force output to stdout to show up when we're running in a container
    sys.stdout.flush()


@app.after_request
def apply_headers(response):
    # This is to force output to stdout to show up when we're running in a container
    sys.stdout.flush()
    # These are to fix low severity vulnerabilities identified by AppScan
    # in a dynamic scan
    response.headers['Content-Security-Policy'] = "object-src 'none'; script-src 'strict-dynamic'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Last-Modified'] = datetime.now()
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


@app.errorhandler(Exception)
def handle_bad_request(e):
    print('Error: %s' % str(e))
    traceback.print_exc()
    error_content = {'Error': str(e)}
    send_sms('Automation error: %s' % str(e))
    return Response(json.dumps(error_content), status=500, mimetype='application/json')

"""
Routine to send a text message through Twilio to alert
"""


def send_sms(msg):
    message = twilio_client.messages.create(
        body=msg,
        from_='+19842144312',
        to='+19192446142'
    )
    return message.sid


def send_mms(media_url):
    if '0.0.0.0' not in request.host:
        message = twilio_client.messages.create(
            from_='+19842144312',
            to='+19192446142',
            media_url=media_url
        )
        return message.sid
    else:
        return None

def get_browser_options():

    if BROWSER == 'Chrome':
        options = ChromeOptions()
        # ref: https://stackoverflow.com/questions/53902507/unknown-error-session-deleted-because-of-page-crash-from-unknown-error-cannot
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        if HEADLESS is True:
            options.headless = True
        else:
            options.headless = False
    elif BROWSER == 'Firefox':
        options = FirefoxOptions()
        if HEADLESS is True:
            options.add_argument("--headless")
    elif BROWSER == 'Safari':
        options = SafariOptions()
        if HEADLESS is True:
            options.headless = True
        else:
            options.headless = False
    elif BROWSER == 'Opera':
        options = OperaOptions()
        if HEADLESS is True:
            options.headless = True
        else:
            options.headless = False
    else:
        options = ChromeOptions()

    return options

@app.route('/')
def automation():
    return render_template('index.html')


@app.route('/webtrac')
def webtrac():
    options = get_browser_options()
    if BROWSER == 'Chrome':
        if docker:
            driver = webdriver.Chrome(options=options)
        else:
            driver = webdriver.Chrome(DRIVER_PATH + CHROME_DRIVER_EXECUTABLE, options=options)
    elif BROWSER == 'Firefox':
        if docker:
            driver = webdriver.Firefox(options=options)
        else:
            firefox_executable = "%s%s" % (DRIVER_PATH, FIREFOX_DRIVER_EXECUTABLE)
            firefox_binary = FirefoxBinary(firefox_executable)
            driver = webdriver.Firefox(firefox_binary=firefox_binary, options=options)
    elif BROWSER == 'Safari':
        driver = webdriver.Safari(options=options)
    elif BROWSER == 'Opera':
        driver = webdriver.Opera(options=options)
    else:
        raise Exception('Invalid value for \'BROWSER\' environment variable')
    driver.set_window_size(1600, 1792)
    wait = WebDriverWait(driver, 5)

    one_week_out = date.fromordinal(date.today().toordinal() + 7)
    one_week_out_month_string = one_week_out.strftime("%m")
    one_week_out_day_string = one_week_out.strftime("%d")
    one_week_out_month = str(int(one_week_out_month_string))
    one_week_out_day = str(int(one_week_out_day_string))
    one_week_out_year = one_week_out.strftime("%Y")

    # This is what the URL looks like when you click the competition pool schedule for 7:00 AM
    # https://webtrac.townofchapelhill.org/wbwsc/webtrac.wsc/search.html?Module=AR&Display=Calendar&CalendarFMID=40440968&BeginMonth=1&BeginYear=2021

    now = datetime.now()
    wait_time_between_tried_in_secs = 120
    total_processing_time_in_secs = 8 * 60 * 60

    webtrac_url = WEBTRAC_HAC

    reservation_url = WEBTRAC_830AM_RESERVATION % (one_week_out_month_string, one_week_out_day_string, one_week_out_year)

    print('================== New Request ====================')
    print('Local time: %s' % now.strftime(' %a - %m/%d - %H:%M:%S'))

    driver.get(WEBTRAC_URL_BASE)
    wait.until(expected_conditions.visibility_of_element_located((By.ID, 'weblogin_username')))
    username_field = driver.find_element_by_id('weblogin_username')
    username_field.clear()
    username_field.send_keys(WEBTRAC_USERID)
    password_field = driver.find_element_by_id('weblogin_password')
    password_field.clear()
    password_field.send_keys(WEBTRAC_PASSWORD)
    login_button = driver.find_element_by_id('xxproclogin')
    login_button.click()
    print('Successfully authenticated.')

    try:
        count = 1
        done = False
        start_time = time.time()
        stop_time = start_time + total_processing_time_in_secs
        while not done and time.time() < stop_time:
            try:
                print('Loading %s' % webtrac_url)
                driver.get(webtrac_url)
                wait.until(expected_conditions.visibility_of_element_located((By.ID, 'content')))
                print('Schedule calendar loaded.')
                # At this point the calendar for this pool schedule is visible

                driver.get(reservation_url)
                print('Attempted to make reservation at %s' % reservation_url)
                print(driver.page_source)
                driver.back()

                # Click the confirmation to add the reservation to shopping cart
                add_button = driver.find_element_by_class_name('websearch_multiselect_buttonaddtocart')
                add_button.click()
                wait.until(expected_conditions.visibility_of_element_located((By.ID, 'content')))
                print('Selected calendar schedule day and confirmed add to cart.')

                # We're logged in, now presented with terms of use, click the checkbox and the click on the
                # continue button.Sometimes these terms do not show up. Don't understand when.
                try:
                    terms_checkbox = driver.find_element_by_id('processingprompts_waivercheckbox')
                    terms_checkbox.click()
                    continue_button = driver.find_element_by_id('processingprompts_buttoncontinue')
                    continue_button.click()
                    print('Accepted terms.')
                except NoSuchElementException:
                    print('Accept terms page not displayed. Skipping.')

                # We may see a selection box asking how did we learn about the program. Look for it and select a reason
                # if present.
                try:
                    learn_about_selection_list = Select(driver.find_element_by_id('question44537618'))
                    learn_about_selection_list.select_by_visible_text("Website")
                    continue_button = driver.find_element_by_id('processingprompts_buttoncontinue')
                    continue_button.click()
                    print('Handled how did you learn about us.')
                except NoSuchElementException:
                    print('How did you learn about us page not displayed. Skipping.')


                # Now, we're at checkout, click the proceed to checkout button
                checkout_button = driver.find_element_by_id('webcart_buttoncheckout')
                checkout_button.click()
                print('Proceeding to checkout.')

                # Continue checkout
                continue_checkout_button = driver.find_element_by_id('webcheckout_buttoncontinue')
                continue_checkout_button.click()
                print('Checked out.')

                done = True
            except Exception as e:
                print('Exception: %s' % e)
                print('Unsuccessful on attempt: %s. Waiting for %s secs.' % (count, wait_time_between_tried_in_secs))
                time.sleep(wait_time_between_tried_in_secs)
                count += 1
                # driver.switch_to.alert.accept()
        if not done:
                raise Exception('Failed to see the desired schedule.')

        # Reservation successful
        send_email_button = driver.find_element_by_id('webconfirmation_buttonsumbit')
        send_email_button.click()
        result_msg = 'Reservation made for %s/%s' % (one_week_out_month, one_week_out_day)
        send_sms(result_msg)

        driver.close()
        response_content = {'Result': result_msg}
        return Response(json.dumps(response_content), status=200, mimetype='application/json')

    except Exception as e:
        print('>>>>>>>> Error <<<<<<<<')
        print(e)
        traceback.print_exc()
        print('Session ID: %s' % driver.session_id)
        response_content = {'Result': 'Error: %s' % e}
        return Response(json.dumps(response_content), status=500, mimetype='application/json')

# def send_screen_cap(driver):
#     r = request
#     now = datetime.now()
#     filename = '/automation/%s.%s.png' % (now.strftime('%m-%d-%H-%M-%S'), uuid.uuid1())
#     mms_url = "http://%s/runtime_images%s" % (r.host, filename)
#     image = driver.get_screenshot_as_png()
#     redis_client.setex(filename, REDIS_TTL, image)
#     send_mms(mms_url)


@app.route('/runtime_images', defaults={'file_path': ''})
@app.route('/runtime_images/<path:file_path>')
def images(file_path):

    if file_path is None or file_path == '':
        matrix_image_names_as_bytes = redis_client.keys()
        matrix_image_names = []
        for entry in matrix_image_names_as_bytes:
            matrix_image_names.append(entry.decode('utf-8'))
        return render_template('images.html', files=matrix_image_names, title='Screen Caps')
    else:
        url_file_path = urllib.parse.quote("/%s" % file_path)
        matrix_bytes = redis_client.get(url_file_path)
        if matrix_bytes is None:
            return abort(404)
        else:
            return Response(matrix_bytes, mimetype='image/png', status=200)

@app.route('/build', methods=['GET', 'POST'])
def build():
    return os.environ['DATE']


@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon-96x96.png')

@app.route('/clear_redis')
def clear_redis():

    keys = redis_client.keys()
    number_of_entries = len(keys)
    for key in keys:
        redis_client.delete(key)
    return Response('Removed %s redis entries' % number_of_entries, mimetype='text/text', status=200)

WEBTRAC_URL_BASE = 'https://webtrac.townofchapelhill.org/'
WEBTRAC_HAC = 'https://webtrac.townofchapelhill.org/wbwsc/webtrac.wsc/search.html?Action=Start&SubAction=&type=AQUA&subtype=HALAPRES&category=&age=&keyword=&keywordoption=Match+One&sort=ActivityNumber&primarycode=&display=Calendar&module=AR&multiselectlist_value=&arwebsearch_buttonsearch=Search'

WEBTRAC_630AM_RESERVATION = 'https://webtrac.townofchapelhill.org/wbwsc/webtrac.wsc/search.html?Action=UpdateSelection&ARFMIDList=46877848&FromProgram=search&GlobalSalesArea_ARItemBeginDate=%s/%s/%s&GlobalSalesArea_ARItemBeginTime=23400&Module=AR'
WEBTRAC_830AM_RESERVATION = 'https://webtrac.townofchapelhill.org/wbwsc/webtrac.wsc/search.html?Action=UpdateSelection&ARFMIDList=46877848&FromProgram=search&GlobalSalesArea_ARItemBeginDate=%s/%s/%s&GlobalSalesArea_ARItemBeginTime=30600&Module=AR'

WEBTRAC_USERID = os.environ['WEBTRAC_USERID']
WEBTRAC_PASSWORD = os.environ['WEBTRAC_PASSWORD']
TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
REDIS_HOST = os.environ['REDIS_HOST']
REDIS_PW = os.environ['REDIS_PW']
REDIS_PORT = os.environ['REDIS_PORT']
REDIS_TTL = 60 * 60 * 48
CHROME_DRIVER_EXECUTABLE = 'chromedriver'
FIREFOX_DRIVER_EXECUTABLE = 'geckodriver'
OPERA_DRIVER_EXECUTABLE = 'operadriver'
DRIVER_PATH = './'


if 'BROWSER' in os.environ:
    BROWSER = os.environ['BROWSER']
    print('Browser: %s' % BROWSER)
else:
    print("Error no BROWSER environment variable defined!")

# Use the presence of HOSTNAME environment variable to determine if we're running in a Docker container
# (HOSTNAME is defined) or locally (no HOSTNAME).
if 'NODE_HOST' in os.environ:
    print('Starting in container')
    docker = True
else:
    print('Starting outside a container')
    docker = False

if 'HEADLESS' in os.environ:
    HEADLESS = os.environ['HEADLESS']
    if HEADLESS == 'True' or HEADLESS == 'true' or HEADLESS == 'TRUE':
        HEADLESS = True
    else:
        HEADLESS = False
else:
    HEADLESS = False
if HEADLESS:
    print('Running headless')
else:
    print('Running with a display')

# Your Account Sid and Auth Token from twilio.com/user/account
account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
twilio_client = Client(account_sid, auth_token)

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PW)

print('Starting %s....' % sys.argv[0])
print('Python: ' + sys.version)
date = os.environ.get('DATE')
if date is None:
    date = 'dev environment'
print('Running build: %s' % date)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))



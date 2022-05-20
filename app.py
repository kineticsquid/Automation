"""
2021
"""
from calendar import c
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions
import redis
import os
from flask import Flask, request, render_template, Response, abort, jsonify
import sys
import traceback
import json
from twilio.rest import Client
import time
from datetime import datetime, date
import uuid
import urllib.parse
import requests
from bs4 import BeautifulSoup

WEBTRAC_URL_BASE = 'https://webtrac.townofchapelhill.org/'
WEBTRAC_HAC = 'https://webtrac.townofchapelhill.org/wbwsc/webtrac.wsc/search.html?Action=Start&SubAction=&type=RES&subtype=HALAPRES&category=&age=&keyword=&keywordoption=Match+One&sort=ActivityNumber&primarycode=&display=Calendar&module=AR&multiselectlist_value=&arwebsearch_buttonsearch=Search'

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
CONTAINER_PATH = '/home/seluser/'
GECKODRIVER_PATH = './geckodriver'
LOG_FILE_NAME = 'geckodriver.log'

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


def send_screen_cap(driver):
    r = request
    now = datetime.now()
    filename = '/automation/%s.%s.png' % (now.strftime('%m-%d-%H-%M-%S'), uuid.uuid1())
    mms_url = "http://%s/runtime_images%s" % (r.host, filename)
    image = driver.get_screenshot_as_png()
    redis_client.setex(filename, REDIS_TTL, image)
    send_mms(mms_url)


def get_driver():
    options = FirefoxOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--headless")
    if os.path.exists(CONTAINER_PATH):
        # We know we're operating in a container - this path is set in Dockerfile
        service = FirefoxService(log_path='%s%s' % (CONTAINER_PATH, LOG_FILE_NAME))
        driver = webdriver.Firefox(service=service, options=options)
    else:
        # Running in a local development environment
        service = FirefoxService(executable_path=GECKODRIVER_PATH)
        driver = webdriver.Firefox(service=service, options=options)
    return driver


@app.route('/')
def automation():
    return render_template('index.html')


@app.route('/webtrac')
def webtrac():
    print('Starting Webtrac request.')

    one_week_out = date.fromordinal(date.today().toordinal() + 7)
    one_week_out_month_string = one_week_out.strftime("%m")
    one_week_out_day_string = one_week_out.strftime("%d")
    one_week_out_month = str(int(one_week_out_month_string))
    one_week_out_day = str(int(one_week_out_day_string))
    one_week_out_year = one_week_out.strftime("%Y")

    now = datetime.now()
    wait_time_between_tried_in_secs = 120
    total_processing_time_in_secs = 8 * 60 * 60

    webtrac_url = WEBTRAC_HAC

    reservation_url = WEBTRAC_830AM_RESERVATION % (one_week_out_month_string, one_week_out_day_string, one_week_out_year)

    print('================== New Request ====================')
    now = datetime.now()
    print('Local time: %s' % now.strftime(' %a - %m/%d - %H:%M:%S'))

    driver = get_driver()
    wait = WebDriverWait(driver, 5)
    driver.get(WEBTRAC_URL_BASE)
    wait.until(expected_conditions.visibility_of_element_located((By.ID, 'weblogin_username')))
    username_field = driver.find_element(By.ID, 'weblogin_username')
    username_field.clear()
    username_field.send_keys(WEBTRAC_USERID)
    password_field = driver.find_element(By.ID, 'weblogin_password')
    password_field.clear()
    password_field.send_keys(WEBTRAC_PASSWORD)
    login_button = driver.find_element(By.ID, 'xxproclogin')
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
                add_button = driver.find_element(By.CLASS_NAME, 'websearch_multiselect_buttonaddtocart')
                add_button.click()
                wait.until(expected_conditions.visibility_of_element_located((By.ID, 'content')))
                print('Selected calendar schedule day and confirmed add to cart.')

                # We're logged in, now presented with terms of use, click the checkbox and the click on the
                # continue button.Sometimes these terms do not show up. Don't understand when.
                try:
                    terms_checkbox = driver.find_element(By.ID, 'processingprompts_waivercheckbox')
                    terms_checkbox.click()
                    continue_button = driver.find_element(By.ID, 'processingprompts_buttoncontinue')
                    continue_button.click()
                    print('Accepted terms.')
                except NoSuchElementException:
                    print('Accept terms page not displayed. Skipping.')

                # We may see a selection box asking how did we learn about the program. Look for it and select a reason
                # if present.
                try:
                    learn_about_selection_list = Select(driver.find_element(By.ID, 'question44537618'))
                    learn_about_selection_list.select_by_visible_text("Website")
                    continue_button = driver.find_element(By.ID, 'processingprompts_buttoncontinue')
                    continue_button.click()
                    print('Handled how did you learn about us.')
                except NoSuchElementException:
                    print('How did you learn about us page not displayed. Skipping.')

                try:
                    # Now, we're at checkout, click the proceed to checkout button
                    checkout_button = driver.find_element(By.ID, 'webcart_buttoncheckout')
                    checkout_button.click()
                    print('Proceeding to checkout.')

                    # Continue checkout
                    continue_checkout_button = driver.find_element(By.ID, 'webcheckout_buttoncontinue')
                    continue_checkout_button.click()
                    print('Checked out.')
                    done = True
                except NoSuchElementException:
                    print('Unable to checkout.')
            except Exception as e:
                print('Exception: %s' % e)
                print('Unsuccessful on attempt: %s. Waiting for %s secs.' % (count, wait_time_between_tried_in_secs))
                if count == 1:
                    send_screen_cap(driver)
                time.sleep(wait_time_between_tried_in_secs)
                count += 1
        if not done:
            raise Exception('Failed to secure a reservation.')

        # Reservation successful
        send_email_button = driver.find_element(By.ID, 'webconfirmation_buttonsumbit')
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


@app.route('/xbox')
def xbox():
    now = datetime.now()
    print('================== New Request ====================')
    print('Local time: %s' % now.strftime(' %a - %m/%d - %H:%M:%S'))
    BEST_BUY_URL = 'https://www.bestbuy.com/site/searchpage.jsp?st=RRT-00001&_dyncharset=UTF-8&_dynSessConf=&id=pcat17071&type=page&sc=Global&cp=1&nrp=&sp=&qp=&list=n&af=true&iht=y&usc=All+Categories&ks=960&keys=keys'
    GAME_STOP_URL = 'https://www.gamestop.com/products/microsoft-xbox-series-x/224744.html'
    ANTONLINE_URL = 'https://www.antonline.com/Microsoft/Electronics/Gaming_Devices/Gaming_Consoles/1438263'

    # Try GameStop
    headers = {'referer': 'https://www.gamestop.com/',
               'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36 OPR/80.0.4170.63'}
    response = requests.get(GAME_STOP_URL, headers=headers)
    if response.status_code != 200:
        raise Exception('HTML error %s retrieving \'%s\'.' % (response.status_code, GAME_STOP_URL))
    html = response.content.decode('utf-8')
    soup = BeautifulSoup(html, "html.parser")
    entries = soup.find_all(id='add-to-cart-buttons')
    if len(entries) == 0:
        raise Exception('Unable to find x-box at Game Stop web site')
    if 'Unavailable' not in entries[0].text:
        result_msg = 'Found it!\n\n%s.' % GAME_STOP_URL
        send_sms(result_msg)
    else:
        result_msg = 'X-box unavailable currently at Gamestop.'
    response_msg = result_msg

    # Try Best Buy
    headers = {'referer': 'https://www.bestbuy.com/',
               'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36 OPR/80.0.4170.63'}
    response = requests.get(BEST_BUY_URL, headers=headers)
    if response.status_code != 200:
        raise Exception('HTML error %s retrieving \'%s\'.' % (response.status_code, BEST_BUY_URL))
    html = response.content.decode('utf-8')
    soup = BeautifulSoup(html, "html.parser")
    list = soup.find_all(class_='sku-item-list')
    entries = soup.find_all(class_='fulfillment-add-to-cart-button')
    combo_entries = soup.find_all(class_='fulfillment-combo-add-to-cart-button')
    entries = entries + combo_entries
    found = False
    for entry in entries:
        if 'Sold Out' not in entry.text:
            result_msg = 'Found it!\n\n%s.' % BEST_BUY_URL
            send_sms(result_msg)
            found = True
            break
    if found:
        response_msg = response_msg + ' %s' % result_msg
    else:
        response_msg = response_msg + ' All %s x-box consoles sold out at Best Buy.' % len(entries)

    print(response_msg)
    response_content = {'Result': response_msg}
    return Response(json.dumps(response_content), status=200, mimetype='application/json')


@app.route('/test-build')
def test_build():
    get_driver()
    return 'Successfully loaded geckodriver.'


@app.route('/build', methods=['GET', 'POST'])
def build():
    try:
        build_file = open('static/build.txt')
        build_stamp = build_file.readlines()[0]
        build_file.close()
    except FileNotFoundError:
        build_stamp = generate_build_stamp()
    results = {
        'Running': '%s %s' % (sys.argv[0], app.name),
        'Python': sys.version,
        'Build': build_stamp,
    }
    return jsonify(results)


def generate_build_stamp():
    return 'Development build - %s' % date.today().strftime("%m/%d/%y")


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


@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon-96x96.png')


@app.route('/clear_redis')
def clear_redis():

    keys = redis_client.keys()
    number_of_entries = len(keys)
    for key in keys:
        redis_client.delete(key)

    results = {
        'Redis entries cleared': number_of_entries
    }
    return jsonify(results)


# Your Account Sid and Auth Token from twilio.com/user/account
account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
twilio_client = Client(account_sid, auth_token)

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PW)

print('Starting %s %s' % (sys.argv[0], app.name))
print('Python: ' + sys.version)

try:
    build_file = open('static/build.txt')
    build_stamp = build_file.readlines()[0]
    build_file.close()
except FileNotFoundError:
    build_stamp = generate_build_stamp()
print('Running build: %s' % build_stamp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


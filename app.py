'''
2023
'''
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
import redis
import os
from flask import Flask, request, render_template, Response, abort, jsonify
import sys
import traceback
import json
from twilio.rest import Client
import time
from datetime import datetime, date
import pytz
import uuid
import urllib.parse
import requests
from bs4 import BeautifulSoup

RWC_TIX_URL = 'https://tickets.rugbyworldcup.com/en'

TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
REDIS_HOST = os.environ['REDIS_HOST']
REDIS_PW = os.environ['REDIS_PW']
REDIS_PORT = os.environ['REDIS_PORT']
HEADLESS = os.environ.get('HEADLESS')
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
    response.headers['Content-Security-Policy'] = 'object-src "none"; script-src "strict-dynamic"'
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
    if '0.0.0.0' not in request.host:
        message = twilio_client.messages.create(
            from_='+19842144312',
            to='+19192446142',
            media_url=media_url
        )
        return message.sid
    else:
        return None

def get_screen_cap(driver):
    r = request
    now = datetime.now()
    filename = '/automation/%s.%s.png' % (now.strftime('%m-%d-%H-%M-%S'), uuid.uuid1())
    mms_url = 'http://%s/runtime_images%s' % (r.host, filename)
    image = driver.get_screenshot_as_png()
    redis_client.setex(filename, REDIS_TTL, image)
    return mms_url

def get_driver():
    options = FirefoxOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    if HEADLESS == 'True':
        print('Running headless')
        options.add_argument('--headless')
    else:
        print('Not running headless')
    if os.path.exists(CONTAINER_PATH):
        # We know we're operating in a container - this path is set in Dockerfile
        print('Running in a container')
        service = FirefoxService(log_path='%s%s' % (CONTAINER_PATH, LOG_FILE_NAME))
        driver = webdriver.Firefox(service=service, options=options)
    else:
        # Running in a local development environment
        print('Not running in a container')
        service = FirefoxService(executable_path=GECKODRIVER_PATH)
        driver = webdriver.Firefox(service=service, options=options)
    size = driver.get_window_size()
    driver.set_window_size(size['width'],size['height']*2)
    return driver

@app.route('/')
def automation():
    return render_template('index.html')

@app.route('/rwc')
def rwc():

    def deal_with_cookie_prompt(driver):
        done = False
        attempt = 1
        while not done:
            try:
                button = driver.find_element(By.ID, "onetrust-accept-btn-handler")
                button.click()
                print('Dismissed cookie pompt.')
                done = True
            except Exception:
                print('Didn\'t see or couldn\'t dismuss cookie pompt.')
                time.sleep(1)
                attempt += 1
            if attempt > 5:
                raise Exception('Could not dismiss cookie prompt after %s attempts.' % attempt)
            else:
                time.sleep(1)

    def get_into_queue(driver):
        driver.get(RWC_TIX_URL)
        print('Loaded home page: %s.' % RWC_TIX_URL)
        time.sleep(1)
        print('Main ticketing page loaded')
        # Now deal with cookie prompt
        enter_buttons = driver.find_elements(By.CLASS_NAME, "btn-primary")
        if len(enter_buttons) == 1 and 'ENTER' in enter_buttons[0].text:
            enter_buttons[0].click()
        print('Clicked to enter queue.')
        time.sleep(1)
    
    def get_past_queue(driver):
        max_attempts = 10
        current_attempt = 1
        done = False
        while not done:
            buttons = driver.find_elements(By.ID, "onetrust-accept-btn-handler")
            if len(buttons) > 0:
                buttons[0].click()
                print('Through queue')
                done = True
            else:
                if current_attempt > max_attempts:
                    url = get_screen_cap(driver)
                    print('Not through queue after max attempts')
                    print('Screen cap: %s' % url)
                    done = True
                else:
                    current_attempt += 1
                    percentages = driver.find_elements(By.CLASS_NAME, "percentage")
                    if len(percentages) > 0:
                        print(percentages[0])
                    print('In queue, waiting 2 seconds')
                    time.sleep(2)


    print('Starting RWC 2023 request.')
    print('================== New Request ====================')
    now = datetime.now()
    print('Local time: %s' % now.strftime(' %a - %m/%d - %H:%M:%S'))

    matches = [
        'EnglandvArgentina',
        'EnglandvJapan'
        ]
    
    def match_match(string):
        found = False
        for match in matches:
            if match in string:
                found = True
                break
        return found

    try:
        driver = get_driver()
        get_into_queue(driver)
        get_past_queue(driver)
        # deal_with_cookie_prompt(driver)
        time.sleep(1)
        tix_results = ''

        # First filter to just England games
        selects = driver.find_elements(By.CLASS_NAME, "js-team-filter")
        selects[0].send_keys('England')
        # selects[0].send_keys('Australia')
        time.sleep(1)
        # Now loop through all offers looking for the matches we want
        offers = driver.find_elements(By.CLASS_NAME, "list-ticket-content")
        for i in range(0, len(offers)):
            offer = offers[i]
            offer_text = offer.text
            if match_match(offer.text):
                print("Matched offer: %s" % offer_text)
                show_button = offer.find_element(By.CLASS_NAME, "js-show-offers")
                show_button.click()
                time.sleep(2)
                print("Clicked offer button")
                offer_modal = driver.find_element(By.CLASS_NAME, "modal-resale-option")
                offer_button = offer_modal.find_element(By.CLASS_NAME, "btn-resale")
                offer_button.click()
                time.sleep(2)
                print("Dismissed offer modal")
                ticket_contents = driver.find_elements(By.CLASS_NAME, "nb-tickets")
                if len(ticket_contents) > 0:
                    print("Found tix")
                    ticket_text = ticket_contents[0].text
                    tix_results = tix_results + '\n%s\n%s' % (offer_text, ticket_text)
                else:
                    print("Found no tix")
                    no_tix = driver.find_element(By.CLASS_NAME, "ticket-content-container")
                    no_tix_text = no_tix.text
                    if 'No ticket' not in no_tix_text:
                        url = get_screen_cap(driver)
                        send_sms('Error in %s' % offer.text)
                        send_mms(url)
                driver.back()
                print("Issued browser back")
                # Need to work by index and refresh the list of results because otherwise they get stale and
                # result in exceptions
                offers = driver.find_elements(By.CLASS_NAME, "list-ticket-content")
        
        driver.close()
        print("Closed driver")
        if len(tix_results) > 0:
            print('Results:')
            print(tix_results)
            send_sms(tix_results)
            send_sms(RWC_TIX_URL)
        else:
            print('No results for:')
            print(json.dumps(matches, indent=4))
        status = 200
    except Exception as e:
        print('Exception: %s' % e)
        get_screen_cap(driver)
        print(traceback.format_exc())
        status = 500

    if len(tix_results) > 0:
        return Response(json.dumps(tix_results), status=status)
    else:
        return Response("No results for %s" % matches, status=status)

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
    soup = BeautifulSoup(html, 'html.parser')
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
    soup = BeautifulSoup(html, 'html.parser')
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
    return 'Development build - %s' % date.today().strftime('%m/%d/%y')


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
        url_file_path = urllib.parse.quote('/%s' % file_path)
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
print('Environment Variables:')
print(json.dumps(dict(os.environ), indent=4))

try:
    build_file = open('static/build.txt')
    build_stamp = build_file.readlines()[0]
    build_file.close()
except FileNotFoundError:
    build_stamp = generate_build_stamp()
print('Running build: %s' % build_stamp)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))


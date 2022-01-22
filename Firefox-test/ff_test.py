from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
import os
from datetime import datetime, date

WEBTRAC_URL_BASE = 'https://webtrac.townofchapelhill.org/'
WEBTRAC_HAC = 'https://webtrac.townofchapelhill.org/wbwsc/webtrac.wsc/search.html?Action=Start&SubAction=&type=RES&subtype=HALAPRES&category=&age=&keyword=&keywordoption=Match+One&sort=ActivityNumber&primarycode=&display=Calendar&module=AR&multiselectlist_value=&arwebsearch_buttonsearch=Search'
WEBTRAC_630AM_RESERVATION = 'https://webtrac.townofchapelhill.org/wbwsc/webtrac.wsc/search.html?Action=UpdateSelection&ARFMIDList=46877848&FromProgram=search&GlobalSalesArea_ARItemBeginDate=%s/%s/%s&GlobalSalesArea_ARItemBeginTime=23400&Module=AR'
WEBTRAC_830AM_RESERVATION = 'https://webtrac.townofchapelhill.org/wbwsc/webtrac.wsc/search.html?Action=UpdateSelection&ARFMIDList=46877848&FromProgram=search&GlobalSalesArea_ARItemBeginDate=%s/%s/%s&GlobalSalesArea_ARItemBeginTime=30600&Module=AR'
WEBTRAC_USERID = os.environ['WEBTRAC_USERID']
WEBTRAC_PASSWORD = os.environ['WEBTRAC_PASSWORD']

one_week_out = date.fromordinal(date.today().toordinal() + 7)
one_week_out_month_string = one_week_out.strftime("%m")
one_week_out_day_string = one_week_out.strftime("%d")
one_week_out_month = str(int(one_week_out_month_string))
one_week_out_day = str(int(one_week_out_day_string))
one_week_out_year = one_week_out.strftime("%Y")

webtrac_url = WEBTRAC_HAC
reservation_url = WEBTRAC_830AM_RESERVATION % (one_week_out_month_string, one_week_out_day_string, one_week_out_year)


options = FirefoxOptions()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument("--headless")
# driver = webdriver.Firefox(service_log_path='/home/seluser/geckodriver.log', options=options)


print('================== New Request ====================')
now = datetime.now()
print('Local time: %s' % now.strftime(' %a - %m/%d - %H:%M:%S'))

service = FirefoxService(log_path='/home/seluser/geckodriver.log')
driver = webdriver.Firefox(service=service)
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

# Now, we're at checkout, click the proceed to checkout button
checkout_button = driver.find_element(By.ID, 'webcart_buttoncheckout')
checkout_button.click()
print('Proceeding to checkout.')

# Continue checkout
continue_checkout_button = driver.find_element(By.ID, 'webcheckout_buttoncontinue')
continue_checkout_button.click()
print('Checked out.')

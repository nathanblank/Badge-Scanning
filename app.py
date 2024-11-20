from flask import Flask, request, render_template, jsonify, render_template_string
import requests
from datetime import datetime
import os
from dotenv import load_dotenv
import csv
import io
import pandas as pd
from thefuzz import process, fuzz
import json
from datetime import datetime
import pytz
# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Airtable configuration
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
BASE_ID = os.getenv('BASE_ID')
EMPLOYEES_TABLE_NAME = os.getenv('EMPLOYEES_TABLE_NAME')
ATTENDANCE_TABLE_NAME = os.getenv('ATTENDANCE_TABLE_NAME')
SCANS_TABLE_NAME = os.getenv('SCANS_TABLE_NAME')

# Airtable API URLs
EMPLOYEES_URL = f'https://api.airtable.com/v0/{BASE_ID}/{EMPLOYEES_TABLE_NAME}'
SCANS_URL = f'https://api.airtable.com/v0/{BASE_ID}/scans'
ATTENDANCE_URL = f'https://api.airtable.com/v0/{BASE_ID}/Attendance'

HEADERS = {
    'Authorization': f'Bearer {AIRTABLE_API_KEY}',
    'Content-Type': 'application/json'
}
badgeNumbers = []
employeesClean = {}
employeesWorkingToday = []
employeesAndRecordID = {}
employeesForDropdown = []
station = ""
currDate = datetime.now()
progress = {'completed_rows': 0, 'total_rows': 0}
employeesWorkingTodayAndRecordID = {}
def post_to_airtable(data):
    """Post data to Airtable and return the response."""
    try:
        response = requests.post(SCANS_URL, headers=HEADERS, json=data)
        response.raise_for_status()  # Raises HTTPError for bad responses
        return response
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Request failed: {e}")
        return None
    
    

def post_drivers_to_airtable(records):
    """Post data to Airtable and return the response."""
    batch_size = 10
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        data = {'records': batch}
        # data = records[i]
        print(data)
        # print(ATTENDANCE_URL)
        response = requests.post(ATTENDANCE_URL, headers=HEADERS, json=data)
        print(response)
        if response.status_code == 200:
            print('Batch uploaded successfully')
        else:
            print(f'Error: {response.status_code}, {response.text}')
    if response.status_code == 200:
        return 200



@app.route('/status', methods=['GET'])
def check_status():
    return jsonify(progress)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Debugging output
        print("Files in request:", request.files)
        station = request.form['station']
        if 'file' not in request.files:
            return jsonify({"message": "No file part"}), 400

        file = request.files['file']
        print("Filename:", file.filename)

        if file.filename == '':
            return jsonify({"message": "No selected file"}), 400

        if file and file.filename.endswith('.csv'):
            try:
            # Read the file using pandas
                file_stream = io.StringIO(file.stream.read().decode('utf-8'))
                df = pd.read_csv(file_stream)
                file_contents = file.stream.read().decode('utf-8')
                csv_reader = csv.reader(io.StringIO(file_contents))
                num_rows = 0

                # Combine first and last names into a new 'Full Name' column
                df['Full Name'] = df['DA First Name'] + ' ' + df['DA Last Name']
                
                # Print the first few rows (for debugging)
                print(df[['DA First Name', 'DA Last Name', 'Full Name']].head())

                # Convert DataFrame to JSON and return response
                
                #loop through each full name and upload to airtable with status "Not Present"
                df = df.sort_values(by=['Full Name'])
                currDate = datetime.now()
                formatted_date = currDate.strftime("%m/%d/%Y")
                airtable_data = []
                for index, row in df.iterrows():
                    # print(row)
                    if(row['Rescuer'] == "\"\""):
                        if(row['Route'] == " "):
                            airtable_data.append({
                            'fields': {
                                'Name': row['Full Name'],
                                'Status': "Not Present",
                                'Station': station,
                                'Route': 'EXTRA',
                                'Staging': '',
                                'Wave': '',
                                'Date': formatted_date
                            }
                        });
                        else:
                            airtable_data.append({
                                'fields': {
                                    'Name': row['Full Name'],
                                    'Status': "Not Present",
                                    'Station': station,
                                    'Route': row['Route'] if pd.notna(row['Route']) else "",  # Check if Route is not NaN
                                    'Staging': row['Staging'][1:-1] if pd.notna(row['Staging']) else "",  # Check if Staging is not NaN
                                    'Wave': row['Parking'] if pd.notna(row['Parking']) else "",  # Check if Wave is not NaN
                                    'Date': formatted_date
                                }
                            });
                    num_rows += 1
                response = post_drivers_to_airtable(airtable_data); 
                if response == 200:
                    return jsonify({'response': 'Success! Record created.', 'rows': num_rows}), 200
            except Exception as e:
                print("Error reading CSV file:", e)
                return jsonify({"message": "Error processing file"}), 505
    return render_template('index.html', message=None)


def updateAllEmployeesAndRecordID():
    global employeesAndRecordID
    employeesAndRecordID = {}
    params = {}
    continueCheck = True
    while (continueCheck == True):
        response = requests.get(EMPLOYEES_URL, headers=HEADERS, params = params)
        data = response.json()
        try:
            params['offset'] = data['offset']
        except:
            continueCheck = False
        for record in data['records']:
            employeesAndRecordID[record['fields']['Name']] = record['id']


@app.route('/api/drivers', methods=['GET'])
def get_drivers():
    global employeesWorkingTodayAndRecordID
    global employeesForDropdown
    global station
    newEmployeesToday = []
    allEmployees = []
    employeesForDropdown = []
    station = request.args.get('station')
    continueCheck = True
    currDate = datetime.now()
    formatted_date = currDate.strftime('%-m/%-d/%Y')
    # print(formatted_date)
    filter_formula = f"AND(AND(IS_SAME({'Date'},'{formatted_date}'), {'Station'} = '{station}'), {'Status'} = 'Not Present')"
    # filter_formula = "IS_SAME(Date,'9/13/2024')"
    params = {
        "filterByFormula": filter_formula,
    }
    while (continueCheck == True):
        # Construct the filter formula
        response = requests.get(ATTENDANCE_URL, headers=HEADERS, params=params)
        data = response.json()
        try:
            params['offset'] = data['offset']
        except:
            continueCheck = False
    
        for record in data['records']:
            employeesForDropdown.append(record['fields']['Name'])
            employeesWorkingTodayAndRecordID[record['fields']['Name']] = record['id']
    
    employeesForDropdown.sort()
    
    
    params = {}
    continueCheck = True
    while (continueCheck == True):
        response = requests.get(EMPLOYEES_URL, headers=HEADERS, params=params)
        data = response.json()
        try:
            params['offset'] = data['offset']
        except:
            continueCheck = False
    
        for record in data['records']:
            allEmployees.append(record['fields']['Name'])

    allEmployees.sort()
    newEmployeesToday = [item for item in employeesForDropdown if item not in allEmployees]
    newEmployeesToday.sort()
    return jsonify(drivers=employeesForDropdown, newDrivers = newEmployeesToday)



@app.route('/scan', methods=['GET', 'POST'])
def scan():
    global badgeNumbers
    global employeesClean
    global employeesWorkingToday
    global employeesAndRecordID
    global currDate
    global station
    unknownEmployee = False
    global employeesWorkingTodayAndRecordID

    # For GET method: Initialize records
    if request.method == 'GET' and "badgeNumber" not in request.full_path:
        # Code for initializing records on GET
        employeesWorkingTodayAndRecordID = {}
        count = 0
        employeesClean = {}
        params = {}
        continueCheck = True
        while continueCheck:
            response = requests.get(EMPLOYEES_URL, headers=HEADERS, params=params)
            data = response.json()
            try:
                params['offset'] = data['offset']
            except KeyError:
                continueCheck = False

            for record in data['records']:
                try:
                    badgeNumber = record['fields']['badgeNumber']
                except KeyError:
                    badgeNumber = str(99999999 - count)
                    count += 1
                employeesClean[badgeNumber] = record['fields']['Name']
        badgeNumbers = list(employeesClean.keys())

        continueCheck = True
        params = {}
        while continueCheck:
            response = requests.get(EMPLOYEES_URL, headers=HEADERS, params=params)
            data = response.json()
            try:
                params['offset'] = data['offset']
            except KeyError:
                continueCheck = False

            for record in data['records']:
                employeesAndRecordID[record['fields']['Name']] = record['id']

    # For POST method: Process the incoming data
    else:
        """Handle POST requests."""
        data = request.get_json()  # Properly extract JSON data from request
        print(f"Data received from frontend: {data}")

        if not data:
            return jsonify({"message": "No data received"}), 400

        # Extract data fields
        badge_number = data.get('badgeNumber', '')
        employeeName = data.get('EmployeeName', '')
        station = data.get('station', '')
        inputType = data.get('inputType', '')
        submissionTime = data.get('submissionTime', '')

        if badge_number != "" and employeeName != "" and badge_number in badgeNumbers:
            # Known employee with correct badge
            pass
        else:
            if badge_number != "99999999":
                if badge_number != "" and badge_number in badgeNumbers:
                    try:
                        employeeName = employeesClean[badge_number]
                    except KeyError:
                        unknownEmployee = True
                        updatingData = {
                            "fields": {
                                "Name": employeeName,
                                "badgeNumber": badge_number
                            }
                        }
                        updateAllEmployeesAndRecordID()
                        updateEmployeeRecordURL = EMPLOYEES_URL + "/" + employeesAndRecordID[employeeName]
                        response = requests.patch(updateEmployeeRecordURL, headers=HEADERS, json=updatingData)
                elif badge_number not in badgeNumbers:
                    updatingData = {
                        "fields": {
                            "Name": employeeName,
                            "badgeNumber": badge_number
                        }
                    }
                    updateAllEmployeesAndRecordID()
                    try:
                        updateEmployeeRecordURL = EMPLOYEES_URL + "/" + employeesAndRecordID[employeeName]
                        response = requests.patch(updateEmployeeRecordURL, headers=HEADERS, json=updatingData)
                    except KeyError:
                        if employeeName != "" and badge_number != "":
                            response = requests.post(EMPLOYEES_URL, headers=HEADERS, json=updatingData)
                        else:
                            return jsonify({"message": "UNKNOWN EMPLOYEE"}), 202

        # Updating attendance
        if not unknownEmployee:
            est_timezone = pytz.timezone('US/Eastern')
            currently = datetime.now(est_timezone)
            ddw7LateTime = currently.replace(hour=9, minute=15, second=0, microsecond=0)
            dmd9LateTime = currently.replace(hour=9, minute=30, second=0, microsecond=0)

            if (station == "DDW7" and currently > ddw7LateTime) or (station == "DMD9" and currently > dmd9LateTime):
                updatingData = {
                    "fields": {
                        "Name": employeeName,
                        "Status": "Late"
                    }
                }
            else:
                updatingData = {
                    "fields": {
                        "Name": employeeName,
                        "Status": "Present"
                    }
                }
            employeesWorkingTodayAndRecordID = {k: employeesWorkingTodayAndRecordID[k] for k in sorted(employeesWorkingTodayAndRecordID)}
            try:
                attendancePostingURL = ATTENDANCE_URL + "/" + employeesWorkingTodayAndRecordID[employeeName]
                response = requests.patch(attendancePostingURL, headers=HEADERS, json=updatingData)
            except KeyError:
                currDate = datetime.now()
                formatted_date = currDate.strftime("%m/%d/%Y")

                updatingData = {
                    "fields": {
                        "Name": employeeName,
                        "Status": "Present but not on schedule",
                        "Date": formatted_date,
                        "Station": station,
                        "Route": "EXTRA",
                        "Staging": "",
                        "Wave": "",
                        "Notes": ""
                    }
                }
                response = requests.post(ATTENDANCE_URL, headers=HEADERS, json=updatingData)
            if response.status_code == 200:
                updated_record = response.json()
                print("Record updated successfully:")
                print(json.dumps(updated_record, indent=2))
            else:
                print(f"Failed to update record: {response.status_code}")
                print(response.json())

        if badge_number and station:
            airtable_data = {
                'fields': {
                    'badgeNumber': badge_number,
                    'station': station,
                    'inputType': inputType,
                    'EmployeeName': employeeName,
                    'submissionTime': submissionTime
                }
            }
            response = post_to_airtable(airtable_data)
            if response and response.status_code == 200:
                if unknownEmployee:
                    return jsonify({"message": "UNKNOWN EMPLOYEE"}), 202
                else:
                    return jsonify({"message": "Success! Record created.", 'employee': employeeName}), 200

            else:
                return jsonify({"message": "Error: Could not create record."}), 507
        else:
            return jsonify({"message": "Error: Badge number is required."}), 400

    return render_template('scan.html', message=None, drivers_working_today=employeesWorkingToday)


if __name__ == '__main__':      
    app.run(debug=True, port=8004)
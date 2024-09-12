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
        print(ATTENDANCE_URL)
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











@app.route('/scan', methods=['GET', 'POST'])
def scan():
    global badgeNumbers
    global employeesClean
    global employeesWorkingToday
    global employeesAndRecordID
    global currDate
    unknownEmployee = False
    global employeesWorkingTodayAndRecordID
    if request.method == 'GET':
        employeesWorkingTodayAndRecordID = {}
        count = 0
        employeesClean = {}
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
                try:
                    badgeNumber = record['fields']['badgeNumber']
                except:
                    badgeNumber = str(99999999 - count)
                    count += 1
                employeesClean[badgeNumber] = record['fields']['Name']
        badgeNumbers = list(employeesClean.keys()) ##TODO FIX BADGENUMBERS
        
        continueCheck = True
        params = {}
        while (continueCheck == True):
            response = requests.get(EMPLOYEES_URL, headers=HEADERS, params = params)
            data = response.json()
            try:
                params['offset'] = data['offset']
            except:
                continueCheck = False
        
            for record in data['records']:
                employeesAndRecordID[record['fields']['Name']] = record['id']
        
        continueCheck = True
        params = {}
        while (continueCheck == True):
            # Construct the filter formula

            filter_formula = f"IS_SAME({'Date'}, TODAY(), 'day')"
            params = {
                "filterByFormula": filter_formula
            }

            response = requests.get(ATTENDANCE_URL, headers=HEADERS, params=params)
            data = response.json()
            try:
                params['offset'] = data['offset']
            except:
                continueCheck = False
        
            for record in data['records']:
                employeesWorkingToday.append(record['fields']['Name'])
                employeesWorkingTodayAndRecordID[record['fields']['Name']] = record['id']
    elif request.method == 'POST':
        """Handle POST requests."""
        data = request.get_json() 
        print(data)
        badge_number = data.get('badgeNumber')  
        employeeName = data.get('EmployeeName', '')
        if(int(badge_number) < 50000000): #check if we have the real badge number
            if badge_number in badgeNumbers: # if that badge number exists
                employeeName = employeesClean[badge_number]
                employeeName = process.extractOne(employeeName, employeesWorkingToday, scorer=fuzz.token_sort_ratio)[0]
            else:
                employeeName = "UNKNOWN EMPLOYEE"
                unknownEmployee = True
        else:
            employeeName = process.extractOne(employeeName, employeesWorkingToday, scorer=fuzz.token_sort_ratio)[0]
        
        #Updating attendance
        if (unknownEmployee == False):
            updatingData = {
                "fields": {
                    "Name": employeeName,
                    "Status": "Present"
                }
            }
            # sendableName = process.extractOne(employeeName, employeesAndRecordID.keys(), scorer=fuzz.token_sort_ratio)[0]
            employeesWorkingTodayAndRecordID = {k: employeesWorkingTodayAndRecordID[k] for k in sorted(employeesWorkingTodayAndRecordID)}
            attendancePostingURL = ATTENDANCE_URL + "/" + employeesWorkingTodayAndRecordID[employeeName]
            response = requests.patch(attendancePostingURL, headers=HEADERS, data=json.dumps(updatingData))
            if response.status_code == 200:
                updated_record = response.json()
                print("Record updated successfully:")
                print(json.dumps(updated_record, indent=2))
            else:
                print(f"Failed to update record: {response.status_code}")
                print(response.json())
            
        station = data.get('station')
        inputType = data.get('inputType')
        submissionTime = data.get('submissionTime')
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

    return render_template('scan.html', message=None)


if __name__ == '__main__':      
    app.run(debug=True, port=8004)

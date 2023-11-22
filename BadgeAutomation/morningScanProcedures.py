# Import the required modules
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

def main():
    # Provide the email and password
    # try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')    
        airtableDriver = webdriver.Chrome("./BadgeAutomation/Drivers/chromedriver")
        
        airtableDriver.get("https://zane4572.softr.app/")
        airtableDriver.implicitly_wait(30)
        time.sleep(15)
        barcodeTable = airtableDriver.find_element(by = By.CLASS_NAME, value = "list-container")
        
        array = barcodeTable.text.split("\n")
        allFormattedRows = {}
        currRow = []
        index = 0
        while index < len(array):
            allFormattedRows[array[index+2]] = array[index]
            index += 3
        # print(allFormattedRows)
        allFormattedRows["009200713611"] = "Maya Rothenberg"
        barcodeInput = ""
        
        employeesScanned = []
        scannedToday = []
        month = time.localtime().tm_mon
        day = time.localtime().tm_mday
        year = time.localtime().tm_year
        try:
            with open('./BadgeAutomation/ScanList/employeeScans' + str(month) + "-" + str(day) + "-" + str(year) + ".txt", 'r+') as file:
                lines = file.readlines()
            for line in lines:
                employeesScanned.append(line[:-1])
                lineArray = line.split(" - ")
                scannedToday.append(lineArray[0])
        except FileNotFoundError:
            print("GOOD MORNING MBBD TEAM\n") #file does not exist so we are going to have to start from scratch
            
        while 1==1:
            print("READY FOR BARCODE\n")
            while barcodeInput == "":
                barcodeInput = input()
            if barcodeInput in allFormattedRows.keys():
                employeeName = allFormattedRows[barcodeInput]
                print(employeeName + " - " + str(time.strftime("%H:%M:%S", time.localtime())) + "\n")
                
                if(employeeName not in scannedToday):
                    scannedToday.append(employeeName)
                    employeesScanned.append(employeeName + " - " + str(time.strftime("%H:%M:%S", time.localtime())))
                    employeesScanned.sort()
                    with open('./BadgeAutomation/ScanList/employeeScans' + str(month) + "-" + str(day) + "-" + str(year) + ".txt", 'w') as file:
                        for employee in employeesScanned:
                            file.write(employee + "\n")
                barcodeInput = ""
            else:
                print("NOT IN SYSTEM: " + barcodeInput + "\n")
                barcodeInput = ""
    # except:
    #     airtableDriver.close()

if __name__ == '__main__':
    main()
    
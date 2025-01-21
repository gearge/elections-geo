#!/usr/bin/env python3
import os
import csv
import sys
import json
# import pandas as pd


number_map_2024 = {
    "01": "მთაწმინდა",
    "02": "ვაკე",
    "03": "საბურთალო",
    "04": "კრწანისი",
    "05": "ისანი",
    "06": "სამგორი",
    "07": "ჩუღურეთი",
    "08": "დიდუბე",
    "09": "ნაძალადევი",
    "10": "გლდანი",
    "11": "საგარეჯო",
    "12": "გურჯაანი",
    "13": "სიღნაღი",
    "14": "დედოფლისწყარო",
    "15": "ლაგოდეხი",
    "16": "ყვარელი",
    "17": "თელავი",
    "18": "ახმეტა",
    "19": "თიანეთი",
    "20": "რუსთავი",
    "21": "გარდაბანი",
    "22": "მარნეული",
    "23": "ბოლნისი",
    "24": "დმანისი",
    "25": "წალკა",
    "26": "თეთრიწყარო",
    "27": "მცხეთა",
    "28": "დუშეთი",
    "29": "ყაზბეგი",
    "30": "კასპი",
    "32": "გორი",
    "33": "ქარელი",
    "35": "ხაშური",
    "36": "ბორჯომი",
    "37": "ახალციხე",
    "38": "ადიგენი",
    "39": "ასპინძა",
    "40": "ახალქალაქი",
    "41": "ნინოწმინდა",
    "43": "ონი",
    "44": "ამბროლაური",
    "45": "ცაგერი",
    "46": "ლენტეხი",
    "47": "მესტია",
    "48": "ხარაგაული",
    "49": "თერჯოლა",
    "50": "საჩხერე",
    "51": "ზესტაფონი",
    "52": "ბაღდათი",
    "53": "ვანი",
    "54": "სამტრედია",
    "55": "ხონი",
    "56": "ჭიათურა",
    "57": "ტყიბული",
    "58": "წყალტუბო",
    "59": "ქუთაისი",
    "60": "ოზურგეთი",
    "61": "ლანჩხუთი",
    "62": "ჩოხატაური",
    "63": "აბაშა",
    "64": "სენაკი",
    "65": "მარტვილი",
    "66": "ხობი",
    "67": "ზუგდიდი",
    "68": "წალენჯიხა",
    "69": "ჩხოროწყუ",
    "70": "ფოთი",
    "79": "ბათუმი",
    "80": "ქედა",
    "81": "ქობულეთი",
    "82": "შუახევი",
    "83": "ხელვაჩაური",
    "84": "ხულო"
}


if __name__ == "__main__":

    os.chdir( os.path.dirname( os.path.abspath(os.sys.argv[0]) ) )

    # --- 2020 ----------------------------------------------------------------

    with open("2020.prop.json", "r") as fh:
        data = json.load(fh)
        
    with open("2020.prop.csv", "w") as fh:
        output = csv.writer(fh)
        numbers = sorted([s["number"] for s in data["items"][0]["subjects"]], key=int)
        output.writerow(["ოლქი - სუბიექტი"] + numbers) # header row
        for item in data["items"]:
            if "Maj" in item["name"]:
                name = "მაჟ.ოლქი"
            elif '|' in item["name"]:
                name = item["name"].split('|')[0] # 0 - GEO, 1 - ENG
            else:
                name = item["name"]
            if int(item['number']) == 0:
                row = [f"{name}"]
            else:
                row = [f"{item['number']}. {name}"]
            _ = {}
            for subject in item["subjects"]:
                _[subject["number"]] = f"{subject['vote']} ({subject['percent']}%)"
            for number in numbers:
                row += [_[number]]
            output.writerow(row)

    # --- 2024 ----------------------------------------------------------------

    with open("2024.prop.json", "r") as fh:
        data = json.load(fh)
        
    with open("2024.prop.csv", "w") as fh:
        output = csv.writer(fh)
        numbers = sorted([s["number"] for s in data["items"][0]["subjects"]], key=int)
        output.writerow(["ოლქი - სუბიექტი"] + numbers) # header row
        for item in data["items"]:
            if "Maj" in item["name"]:
                name = "მაჟ.ოლქი"
            elif '|' in item["name"]:
                name = item["name"].split('|')[0] # 0 - GEO, 1 - ENG
            else:
                name = item["name"]
                if int(item['number']) == 0:
                    row = [f"{name}"]
                else:
                    number = item['number']
                    row = [f"{number}.{number_map_2024[number]}"]
            _ = {}
            for subject in item["subjects"]:
                _[subject["number"]] = f"{subject['votes']} ({subject['percent']}%)"
            for number in numbers:
                row += [_[number]]
            output.writerow(row)

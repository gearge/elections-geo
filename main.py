#!/usr/bin/env python3
# Compare election results in Georgia using JSON and HTML table data from
# https://results.cec.gov.ge and https://archiveresults.cec.gov.ge
#
# Created 2024-12-15 by Giorgi Tavkelishvili <giorgi@linuxpg.org>
# Updated 2025-01-10 by Giorgi Tavkelishvili <giorgi@linuxpg.org>
#
# Copyright (c) 2024 Giorgi Tavkelishvili <giorgi@linuxpg.org>
# Released under The MIT License: https://opensource.org/license/MIT

import os
import re
import csv
import copy
import json
import math
import pprint
from collections import OrderedDict

class ElectionGeo:

    ELECTORAL_THRESHOLDS = {
        2012: {
            "proportional": 5,
            "majoritarian": 50
        },
        2016: {
            "proportional": 5,
            "majoritarian": 50
        },
        2020: {
            "proportional": 1,
            "majoritarian": 50
        },
        2024: {
            "proportional": 5
        }
    }

    ABROAD_DISTRICT = {
        2012: "87",
        2016: "0",
        2020: "0",
        2024: "0"
    }

    # Districts of Tbilisi for each election year: Vake, Saburtalo...
    TBILISI_DISTRICTS = {
        2012: {
            "1": "მთაწმინდა",
            "2": "ვაკე",
            "3": "საბურთალო",
            "4": "კრწანისი",
            "5": "ისანი",
            "6": "სამგორი",
            "7": "ჩუღურეთი",
            "8": "დიდუბე",
            "9": "ნაძალადევი",
            "10": "გლდანი"
        }, # E.g. obj["items"][1]["number"] == "1"
        2016: {
            "1": "მთაწმინდა",
            "2": "ვაკე",
            "3": "ვაკე",
            "4": "საბურთალო",
            "5": "საბურთალო",
            "6": "საბურთალო",
            "7": "კრწანისი",
            "8": "ისანი",
            "9": "ისანი",
            "10": "ისანი",
            "11": "სამგორი",
            "12": "სამგორი",
            "13": "სამგორი",
            "14": "ჩუღურეთი",
            "15": "დიდუბე",
            "16": "დიდუბე",
            "17": "ნაძალადევი",
            "18": "ნაძალადევი",
            "19": "ნაძალადევი",
            "20": "გლდანი",
            "21": "გლდანი",
            "22": "გლდანი",
        }, # E.g. obj["items"][1]["number"] == "1"
        2020: {
            "1": "მთაწმინდა,კრწანისი",
            "2": "ვაკე",
            "3": "საბურთალო",
            "4": "ისანი",
            "5": "სამგორი",
            "6": "ჩუღურეთი,დიდუბე",
            "7": "ნაძალადევი",
            "8": "გლდანი"
        }, # E.g. obj["items"][1]["number"] == "1"
        2024: {
            "01": "მთაწმინდა",
            "02": "ვაკე",
            "03": "საბურთალო",
            "04": "კრწანისი",
            "05": "ისანი",
            "06": "სამგორი",
            "07": "ჩუღურეთი",
            "08": "დიდუბე",
            "09": "ნაძალადევი",
            "10": "გლდანი"
        } # E.g. obj["items"][1]["number"] == "01"
    }

    def __init__(self, year: int, type: str, file: str, debug=True):
        self.year = year
        self.type = type
        self.file = file
        self.debug = debug
        self.details = None
        self.party_name_by_number = {}
        self.vote_pcts_by_number = { "abroad": {}, "tbilisi": {}, "other": {} }
        self.vote_pcts_by_number_avg = { "abroad": {}, "tbilisi": {}, "other": {} }
        self.vote_counts_by_number = { "abroad": {}, "tbilisi": {}, "other": {} }
        self.vote_counts_by_number_sum = { "abroad": {}, "tbilisi": {}, "other": {} }
        self.vote_counts_by_number_sum_all = OrderedDict()
        self.party_numbers_pass_electoral_threshold = []

        if self.type != 'proportional':
            raise NotImplementedError("Support for majoritarian elections has not yet been implemented!")

    def _is_valid_json(self) -> bool:
        # TODO: Implement JSON schema validation and add to __init__()
        return True

    def _are_valid_items(self, items: list) -> bool:
        if len(items) == 0:
            print(f"ERROR: Empty list parameter 'items' supplied to 'self._are_valid_items()' method of '{type(self).__name__}' instance")
            return False
        elif len(items) > 1:
            # Extract party numbers from the 1st entry
            all_party_numbers = sorted([s["number"] for s in items[0]["subjects"]], key=lambda x: int(x)) 
            if self.debug: print(f"DEBUG: all_party_numbers: {all_party_numbers}")

            for item in items[1:]:
                # "item" - dict containing results for all parties from one proportional district
                district_party_numbers = sorted([s["number"] for s in item["subjects"]], key=lambda x: int(x))
                if district_party_numbers != all_party_numbers:
                    print(f"ERROR: List of parties from proportional district {item['number']} ({item['name']}) {district_party_numbers} not the same as {all_party_numbers}")
                    return False
        
        return True

    def _load_json(self) -> None:
        with open(self.file, 'r') as fh:
            self.details = json.load(fh)

    def _load_normalize_csv(self) -> None:
        template_subject = {
            #"id": 0,
            "name": "სუბიექტი",
            "number": "0",
            "percent": 0.0,
            "votes": 0
        }
        template_item = {
            #"id": 0,
            "name": "ოლქი",
            "number": "0",
            "subjects": [
                # template_subject ...
            ]
        }
        template_details = {
            "info": {
                "canceled": 0,
                "counted": 0,
                "countedPercent": 0.0,
                "foreign": 0,
                "total": 0
            },
            "items": [
                # template_item ...
            ]
        }

        with open(self.file, 'r') as fh:
            csv_obj = csv.DictReader(fh)
            self.details = copy.deepcopy(template_details) # don't do template_details.copy() (shallow copy) due to a nested list!
            for d in csv_obj:
                item = copy.deepcopy(template_item) # don't do template_item.copy() (shallow copy) due to a nested list!

                __ = d['ოლქი - სუბიექტი']
                item["name"] = __
                if __ == 'საზღვარგარეთი':
                    item["number"] = "0"
                else:
                    # E.g. '#1 მაჟ. ოლქი'
                    item["number"] = re.findall("\d+", __)[0] # e.g. '1'
                
                for _number, _votes_pct in d.items():
                    # E.g. '41', '12628\n(51.11%)'
                    if _number != 'ოლქი - სუბიექტი':
                        subject = template_subject.copy()
                        subject["name"] = '?' # TODO:
                        subject["number"] = _number
                        subject["votes"]   = int(_votes_pct.split('\n')[0])                                      # e.g. 12628
                        subject["percent"] = float(re.findall("(\d+(\.\d+)?)", _votes_pct.split('\n')[1])[0][0]) # e.g. 51.11
                        item["subjects"] += [subject]

                self.details["items"] += [item]

    def _load_details(self) -> None:
        if self.file.lower().endswith('.json'):
            self._load_json()
        elif self.file.lower().endswith('.csv'):
            self._load_normalize_csv()
        else:
            pass # TODO: handle other, incl. stream

    def _get_party_name(self, name: str) -> str:
        if '|' in name:
            return name.split('|')[1] # 0 - Georgian, 1 - English
        else:
            return name

    def _get_details_for_region(self, region: str) -> list:
        # region in ["abroad", "tbilisi", "other"]
        __ = []
        if region == "abroad":
            for item in self.details['items']:
                if item["number"] == self.ABROAD_DISTRICT[int(self.year)]:
                    __ = [item]
                    break
        elif region == "tbilisi":
            for item in self.details['items']:
                if item["number"] in self.TBILISI_DISTRICTS[int(self.year)]:
                    __ += [item]
        elif region == "other":
            for item in self.details['items']:
                if item["number"] not in list(self.ABROAD_DISTRICT[int(self.year)]) + list(self.TBILISI_DISTRICTS[int(self.year)].keys()):
                    __ += [item]
        return __

    # Populates self.party_name_by_number dict
    def _set_party_name_by_number(self) -> None:
        for d in self._get_details_for_region("abroad"):
            # "d" - dict containing results for all parties from one proportional district
            for subject in d['subjects']:
                _name = subject['name']
                _number = subject['number']
                if _number not in self.party_name_by_number:
                    self.party_name_by_number[_number] = self._get_party_name(_name)

    # Populates self.vote_pcts_by_number dict
    def _set_vote_pcts_by_number(self, details: list, region: str) -> None:
        for d in details:
            # "d" - dict containing results for all parties from one proportional district
            for subject in d['subjects']:
                _number = subject['number']
                _percent = subject['percent']
                if _number not in self.vote_pcts_by_number[region]:
                    self.vote_pcts_by_number[region][_number] = [ _percent ]
                else:
                    self.vote_pcts_by_number[region][_number] += [ _percent ]

    def _get_vote_from_subject(self, subject: dict) -> int:
        if "votes" in subject:
            return int(subject['votes'])
        else:
            return int(subject['vote'])

    # Populates self.vote_counts_by_number dict
    def _set_vote_counts_by_number(self, details: list, region: str) -> None:
        for d in details:
            # "d" - dict containing results for all parties from one proportional district
            for subject in d['subjects']:
                _number = subject['number']
                _votes = self._get_vote_from_subject(subject)
                if _number not in self.vote_counts_by_number[region]:
                    self.vote_counts_by_number[region][_number] = [ _votes ]
                else:
                    self.vote_counts_by_number[region][_number] += [ _votes ]

    # Populates self.vote_pcts_by_number_avg dict based on values from self.vote_pcts_by_number
    def _set_vote_pcts_by_number_avg(self, region: str) -> None:
        for _number, _vote_pcts in self.vote_pcts_by_number[region].items():
            # if self.debug: print("DEBUG: _number _vote_pcts:", _number, _vote_pcts)
            self.vote_pcts_by_number_avg[region][_number] = sum(_vote_pcts)/len(_vote_pcts)

    def _set_vote_counts_by_number_sum(self, region: str) -> None:
        for _number, _votes in self.vote_counts_by_number[region].items():
            self.vote_counts_by_number_sum[region][_number] = sum(_votes)

    def _set_vote_counts_by_number_sum_all(self) -> None:
        for _number in sorted(self.vote_counts_by_number_sum["abroad"].keys(), key=int):
            _sum = sum([self.vote_counts_by_number_sum['tbilisi'][_number], self.vote_counts_by_number_sum['other'][_number], self.vote_counts_by_number_sum['abroad'][_number]])
            self.vote_counts_by_number_sum_all[_number] = _sum

    def _set_party_numbers_pass_electoral_threshold(self) -> None:
        _total = 0
        for _number, _sum in self.vote_counts_by_number_sum_all.items():
            _total += _sum
        
        _min_votes_required = math.ceil( self.ELECTORAL_THRESHOLDS[self.year][self.type]*(_total/100) )
        for _number, _sum in self.vote_counts_by_number_sum_all.items():
            if _sum >= _min_votes_required:
                self.party_numbers_pass_electoral_threshold.append(_number)

    def _get_vote_pcts_by_number_avg_pass(self, region: str) -> dict:
        vote_pcts_by_number_avg_pass = {}
        for _number, _pct_avg in self.vote_pcts_by_number_avg[region].items():
            if _number in self.party_numbers_pass_electoral_threshold:
                vote_pcts_by_number_avg_pass[_number] = _pct_avg
        return vote_pcts_by_number_avg_pass

    def _get_vote_pcts_by_number_avg_pass_not_41_sum(self, region: str) -> float:
        vote_pcts_by_number_avg_pass_not_41_sum = 0
        for _number, _pct_avg in self._get_vote_pcts_by_number_avg_pass(region).items():
            if int(_number) != 41:
                vote_pcts_by_number_avg_pass_not_41_sum += _pct_avg
        return vote_pcts_by_number_avg_pass_not_41_sum

    def get_votes_by_number_pct_avg_pass(self, region: str, target: str) -> float:
        if target == '41':
            return self._get_vote_pcts_by_number_avg_pass(region)['41']
        else:
            return self._get_vote_pcts_by_number_avg_pass_not_41_sum(region)

    def _get_vote_count_by_number_sum_pass_not_41(self, region: str) -> float:
        vote_count_by_number_sum_pass_not_41 = 0
        # 1st obtain numbers/IDs for parties pass the electoral threshold
        for _number in self.party_numbers_pass_electoral_threshold:
            if int(_number) != 41:
                vote_count_by_number_sum_pass_not_41 += self.vote_counts_by_number_sum[region][_number]
        return vote_count_by_number_sum_pass_not_41

    def get_votes_by_number_count_sum_pass(self, region: str, target: str) -> float:
        if target == '41':
            return self.vote_counts_by_number_sum[region]['41']
        else:
            return self._get_vote_count_by_number_sum_pass_not_41(region)

    def main(self) -> None:
        self._load_details()
        if self.debug:
            with open(f"details.{self.year}.txt", "w") as fh:
                pprint.pprint(self.details, indent=4, stream=fh)

        details_abroad = self._get_details_for_region("abroad") # data from abroad
        if self.debug: print(f"DEBUG: details_abroad: {details_abroad}") 
        details_tbilisi = self._get_details_for_region("tbilisi") # data from Tbilisi
        if self.debug: print(f"DEBUG: len(details_tbilisi): {len(details_tbilisi)}") 
        details_other = self._get_details_for_region("other") # data from other regions
        if self.debug: print(f"DEBUG: len(details_other): {len(details_other)}") 

        if not self._are_valid_items(details_tbilisi):
            raise ValueError("Invalid items in data from Tbilisi ('details_tbilisi' var in 'main()')")
        if not self._are_valid_items(details_other):
            raise ValueError("Invalid items in data from other regions ('details_other' var in 'main()')")
        if not self._are_valid_items(details_abroad):
            raise ValueError("Invalid items in data from abroad ('details_abroad' var in 'main()')")

        self._set_party_name_by_number()
        if self.debug: print("DEBUG: self.party_name_by_number:", self.party_name_by_number)

        self._set_vote_counts_by_number(details_tbilisi, "tbilisi")
        if self.debug: print("DEBUG: self.vote_counts_by_number['tbilisi']:", self.vote_counts_by_number['tbilisi'])
        self._set_vote_counts_by_number_sum("tbilisi")
        if self.debug: print("DEBUG: self.vote_counts_by_number_sum['tbilisi']:", self.vote_counts_by_number_sum['tbilisi'])
        self._set_vote_counts_by_number(details_other, "other")
        if self.debug: print("DEBUG: self.vote_counts_by_number['other']:", self.vote_counts_by_number['other'])
        self._set_vote_counts_by_number_sum("other")
        if self.debug: print("DEBUG: self.vote_counts_by_number_sum['other']:", self.vote_counts_by_number_sum['other'])
        self._set_vote_counts_by_number(details_abroad, "abroad")
        if self.debug: print("DEBUG: self.vote_counts_by_number['abroad']:", self.vote_counts_by_number['abroad'])
        self._set_vote_counts_by_number_sum("abroad")
        if self.debug: print("DEBUG: self.vote_counts_by_number_sum['abroad']:", self.vote_counts_by_number_sum['abroad'])

        self._set_vote_counts_by_number_sum_all()
        if self.debug: print("DEBUG: self.vote_counts_by_number_sum_all:", self.vote_counts_by_number_sum_all)
        self._set_party_numbers_pass_electoral_threshold()
        if self.debug: print("DEBUG: self.party_numbers_pass_electoral_threshold:", self.party_numbers_pass_electoral_threshold)
        if self.debug:
            print("DEBUG:", f"    {self.year}")
            print("DEBUG:", "-" * 11)
            _total = 0
            for _number, _sum in self.vote_counts_by_number_sum_all.items():
                _total += _sum
                print("DEBUG:", f"{_number:<2}: {_sum}")
            print("DEBUG:", "-" * 11)
            print("DEBUG:", f"    {_total}")

        self._set_vote_pcts_by_number(details_tbilisi, "tbilisi")
        if self.debug: print("DEBUG: self.vote_pcts_by_number['tbilisi']:", self.vote_pcts_by_number['tbilisi'])
        self._set_vote_pcts_by_number_avg("tbilisi")
        if self.debug: print("DEBUG: self.vote_pcts_by_number_avg['tbilisi']:", self.vote_pcts_by_number_avg['tbilisi'])
        self._set_vote_pcts_by_number(details_other, "other")
        if self.debug: print("DEBUG: self.vote_pcts_by_number['other']:", self.vote_pcts_by_number['other'])
        self._set_vote_pcts_by_number_avg("other")
        if self.debug: print("DEBUG: self.vote_pcts_by_number_avg['other']:", self.vote_pcts_by_number_avg['other'])
        self._set_vote_pcts_by_number(details_abroad, "abroad")
        if self.debug: print("DEBUG: self.vote_pcts_by_number['abroad']:", self.vote_pcts_by_number['abroad'])
        self._set_vote_pcts_by_number_avg("abroad")
        if self.debug: print("DEBUG: self.vote_pcts_by_number_avg['abroad']:", self.vote_pcts_by_number_avg['abroad'])

class ElectionGeoPrinter():

    def __init__(self, election_geo_objs: list):
        self.election_geo_objs = election_geo_objs

    def _format_row(self, row: list) -> str:
        __ = '{:<38}'.format(row[0])
        for col in row[1:]:
            __ += ' | {:<33}'.format(col)
        return __

    def print(self) -> None:
        # --- Tbilisi ---

        head_tbilisi = ["Tbilisi (all districts) averaged"]
        for election_geo in self.election_geo_objs:
            head_tbilisi += [f"{election_geo.year} {election_geo.type} ({election_geo.ELECTORAL_THRESHOLDS[election_geo.year][election_geo.type]}% threshold)"]
        __ = self._format_row(head_tbilisi)
        print(__, '-' * len(__), sep='\n')

        rows_tbilisi = [ [f"41: {election_geo.party_name_by_number['41']}"], ["Sum of others pass electoral threshold"] ]
        _vote_pcts_prev = None
        for i, election_geo in enumerate(self.election_geo_objs):
            _vote_pct_41 = election_geo.get_votes_by_number_pct_avg_pass('tbilisi', '41')
            _vote_count_41 = election_geo.get_votes_by_number_count_sum_pass('tbilisi', '41')
            __ = f"{_vote_count_41:,} {round(_vote_pct_41, 2)}%"
            if i > 0: __ += f" ({_vote_count_41 - _vote_counts_prev['41']:+,} {round(_vote_pct_41 - _vote_pcts_prev['41'], 2):+}%)"
            rows_tbilisi[0] += [__]

            _vote_pct_others = election_geo.get_votes_by_number_pct_avg_pass('tbilisi', 'others')
            _vote_count_others = election_geo.get_votes_by_number_count_sum_pass('tbilisi', 'others')
            __ = f"{_vote_count_others:,} {round(_vote_pct_others, 2)}%"
            if i > 0: __ += f" ({_vote_count_others - _vote_counts_prev['others']:+,} {round(_vote_pct_others - _vote_pcts_prev['others'], 2):+}%)"
            rows_tbilisi[1] += [__]

            _vote_pcts_prev = {'41': _vote_pct_41, 'others': _vote_pct_others}
            _vote_counts_prev = {'41': _vote_count_41, 'others': _vote_count_others}
        for row in rows_tbilisi:
            print(self._format_row(row))

        # --- Other regions ---
        print("")

        head_other = ["Other regions averaged"]
        for election_geo in self.election_geo_objs:
            head_other += [f"{election_geo.year} {election_geo.type} ({election_geo.ELECTORAL_THRESHOLDS[election_geo.year][election_geo.type]}% threshold)"]
        __ = self._format_row(head_other)
        print(__, '-' * len(__), sep='\n')

        rows_other = [ [f"41: {election_geo.party_name_by_number['41']}"], ["Sum of others pass electoral threshold"] ]
        _vote_pcts_prev = None
        for i, election_geo in enumerate(self.election_geo_objs):
            _vote_pct_41 = election_geo.get_votes_by_number_pct_avg_pass('other', '41')
            _vote_count_41 = election_geo.get_votes_by_number_count_sum_pass('other', '41')
            __ = f"{_vote_count_41:,} {round(_vote_pct_41, 2)}%"
            if i > 0: __ += f" ({_vote_count_41 - _vote_counts_prev['41']:+,} {round(_vote_pct_41 - _vote_pcts_prev['41'], 2):+}%)"
            rows_other[0] += [__]

            _vote_pct_others = election_geo.get_votes_by_number_pct_avg_pass('other', 'others')
            _vote_count_others = election_geo.get_votes_by_number_count_sum_pass('other', 'others')
            __ = f"{_vote_count_others:,} {round(_vote_pct_others, 2)}%"
            if i > 0: __ += f" ({_vote_count_others - _vote_counts_prev['others']:+,} {round(_vote_pct_others - _vote_pcts_prev['others'], 2):+}%)"
            rows_other[1] += [__]

            _vote_pcts_prev = {'41': _vote_pct_41, 'others': _vote_pct_others}
            _vote_counts_prev = {'41': _vote_count_41, 'others': _vote_count_others}
        for row in rows_other:
            print(self._format_row(row))

        # --- Abroad ---
        print("")

        head_abroad = ["Abroad"]
        for election_geo in self.election_geo_objs:
            head_abroad += [f"{election_geo.year} {election_geo.type} ({election_geo.ELECTORAL_THRESHOLDS[election_geo.year][election_geo.type]}% threshold)"]
        __ = self._format_row(head_abroad)
        print(__, '-' * len(__), sep='\n')

        rows_abroad = [ [f"41: {election_geo.party_name_by_number['41']}"], ["Sum of others pass electoral threshold"] ]
        _vote_pcts_prev = None
        for i, election_geo in enumerate(self.election_geo_objs):
            _vote_pct_41 = election_geo.get_votes_by_number_pct_avg_pass('abroad', '41')
            _vote_count_41 = election_geo.get_votes_by_number_count_sum_pass('abroad', '41')
            __ = f"{_vote_count_41:,} {round(_vote_pct_41, 2)}%"
            if i > 0: __ += f" ({_vote_count_41 - _vote_counts_prev['41']:+,} {round(_vote_pct_41 - _vote_pcts_prev['41'], 2):+}%)"
            rows_abroad[0] += [__]

            _vote_pct_others = election_geo.get_votes_by_number_pct_avg_pass('abroad', 'others')
            _vote_count_others = election_geo.get_votes_by_number_count_sum_pass('abroad', 'others')
            __ = f"{_vote_count_others:,} {round(_vote_pct_others, 2)}%"
            if i > 0: __ += f" ({_vote_count_others - _vote_counts_prev['others']:+,} {round(_vote_pct_others - _vote_pcts_prev['others'], 2):+}%)"
            rows_abroad[1] += [__]

            _vote_pcts_prev = {'41': _vote_pct_41, 'others': _vote_pct_others}
            _vote_counts_prev = {'41': _vote_count_41, 'others': _vote_count_others}
        for row in rows_abroad:
            print(self._format_row(row))
        
        # --- Totals ---
        print("")

        head_total = ["Voter participation"]
        for election_geo in self.election_geo_objs:
            head_total += [f"{election_geo.year} {election_geo.type}"]
        __ = self._format_row(head_total)
        print(__, '-' * len(__), sep='\n')

        rows_total = [ ["Total valid"] ]
        _total_prev = 0
        for i, election_geo in enumerate(self.election_geo_objs):
            _total = 0
            for _number, _sum in election_geo.vote_counts_by_number_sum_all.items():
                _total += _sum
            __ = f"{_total:,}"
            if i > 0: __ += f" ({_total - _total_prev:+,})"
            rows_total[0] += [__]
            _total_prev = _total
        for row in rows_total:
            print(self._format_row(row))


if __name__ == '__main__':

    os.chdir( os.path.dirname( os.path.abspath(os.sys.argv[0]) ) )

    election_geo_2012_prop = ElectionGeo(year=2012, type='proportional', file='2012.proporciuli.csv', debug=False)
    election_geo_2012_prop.main()
    election_geo_2016_prop = ElectionGeo(year=2016, type='proportional', file='2016.proporciuli.csv', debug=False)
    election_geo_2016_prop.main()
    election_geo_2020_prop = ElectionGeo(year=2020, type='proportional', file='2020.prop.json', debug=False)
    election_geo_2020_prop.main()
    election_geo_2024_prop = ElectionGeo(year=2024, type='proportional', file='2024.prop.json', debug=False)
    election_geo_2024_prop.main()
    election_geo_printer = ElectionGeoPrinter([election_geo_2012_prop, election_geo_2016_prop, election_geo_2020_prop, election_geo_2024_prop]) # order of objects is important
    election_geo_printer.print()

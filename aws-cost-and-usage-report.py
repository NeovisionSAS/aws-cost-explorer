#!/usr/bin/env python

import argparse
import dateutil.relativedelta as dateutil
import datetime
import os
import sys
import functools

import boto3
import botocore.exceptions

DATETIME_NOW = datetime.datetime.utcnow()
AWS_COST_EXPLORER_SERVICE_KEY = "ce"
OUTPUT_FILE_NAME = "report.csv"
OUTPUT_FILE_HEADER_LINE = ",".join(
    ["Time Period", "Organization", "Project", "Amount",
     "Unit", "Estimated", "\n"])
CURRENT_FOLDER_PATH = os.path.abspath(os.path.curdir)
DEFAULT_OUTPUT_FILE_PATH = os.path.join(CURRENT_FOLDER_PATH, OUTPUT_FILE_NAME)
COST_EXPLORER_GRANULARITY_MONTHLY = "MONTHLY"
COST_EXPLORER_GRANULARITY_DAILY = "DAILY"

COST_EXPLORER_GROUP_BY = [
    {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"},
    {"Type": "DIMENSION", "Key": "SERVICE"}]

COST_EXPLORER_GROUP_BY_PROJECT = [
    {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"},
    {"Type": "TAG", "Key": "Project"}]


def main():
    daily, monthly, enable_total, output_file, profile_name, env_auth = process_args(
        create_parser())
    try:
        if env_auth:
            session = boto3.Session(aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))
        else:
            session = boto3.Session(profile_name=profile_name)
    except botocore.exceptions.ProfileNotFound as exp:
        print("Error: %s" % str(exp))
        sys.exit(1)
    except Exception as e:
        print("Error: %s" % str(e))
        sys.exit(1)
    cost_explorer = session.client(AWS_COST_EXPLORER_SERVICE_KEY)
    aws_name = session.client("organizations")
    granularity = COST_EXPLORER_GRANULARITY_MONTHLY
    if daily:
        granularity = COST_EXPLORER_GRANULARITY_DAILY
    write_output_file(
        output_file,
        aws_name,
        get_cost_and_usage(
            cost_explorer,
            granularity,
            daily,
            monthly),
        enable_total,
        monthly)
    print("\nOutput written to: %s" % output_file)


def process_args(parser):
    args = parser.parse_args()
    days, months = args.days, args.months
    if (type(days) is int) and (type(months) is int):
        parser.print_help()
        print("Error: 'days' and 'months' options are mutually exclusive.")
        sys.exit(1)
    if days is None and months is None:
        days, months = 0, 1
    output_fpath = args.fpath
    enable_total = not args.disable_total
    profile_name = args.profile_name
    env_auth = args.env_auth
    return days, months, enable_total, output_fpath, profile_name, env_auth


def create_parser():
    parser = argparse.ArgumentParser(
        description="AWS Simple Cost and Usage Report")
    parser.add_argument(
        "--output",
        dest="fpath",
        default=DEFAULT_OUTPUT_FILE_PATH,
        help="output file path (default:%s)" % OUTPUT_FILE_NAME)
    parser.add_argument(
        "--profile-name",
        dest="profile_name",
        help="Profile name on your AWS account")
    parser.add_argument(
        "--days",
        type=int,
        dest="days",
        default=None,
        help="get data for daily usage and cost by given days.\
             (Mutualy exclusive with 'months' option, default: 0)")
    parser.add_argument(
        "--months",
        type=int,
        dest="months",
        default=None,
        help="get data for monthly usage and cost by given months. \
             (Mutualy exclusive with 'days' option, default: 1)")
    parser.add_argument(
        "--env-auth",
        action="store_true",
        default=False,
        help="Will use AWS_ACCES_KEY_ID and AWS_SECRET_ACCESS_KEY env \
             variables to initialize the session.")
    parser.add_argument(
        "--disable-total",
        action="store_true",
        default=False,
        help="Do not output total cost per day, or month unit.")
    return parser


def get_cost_and_usage(cost_explorer, granularity, days, months, only_full_month=True):
    time_period = {
        "Start": get_cost_start_period(days, months),
        "End": DATETIME_NOW.strftime("%Y-%m-01") if only_full_month else DATETIME_NOW.strftime("%Y-%m-%d")}
    token = None
    result = []
    while True:
        kwargs = {}
        if token:
            kwargs = {"NextPageToken": token}
        data = cost_explorer.get_cost_and_usage(
            TimePeriod=time_period,
            Granularity=granularity,
            Metrics=["UnblendedCost"],
            GroupBy=COST_EXPLORER_GROUP_BY_PROJECT, **kwargs)
        result += data["ResultsByTime"]
        token = data.get("NextPageToken", None)
        if not token:
            break
    return result


def get_cost_start_period(days, months):
    start_strftime = None
    # it crashed the first day of the month, because it gave the same start and end date
    if months:
        if months == 1:
            start_strftime = DATETIME_NOW.strftime("%Y-%m-01")
            if DATETIME_NOW.day == 1:
                # if we are the first of the month, we cannot get the "today to today" cost, so we get the last month
                start_strftime = (DATETIME_NOW - dateutil.relativedelta(months=1)).strftime("%Y-%m-01")
        else:
            prev_month = DATETIME_NOW - dateutil.relativedelta(months=months - 1)
            start_strftime = prev_month.strftime("%Y-%m-01")
    if days:
        prev_day = DATETIME_NOW - datetime.timedelta(days=days)
        start_strftime = prev_day.strftime("%Y-%m-%d")
    return start_strftime


def write_output_file(output_file, aws_name, cost_and_usage_data, enable_total, monthly):
    with open(output_file, "w") as output_file_:
        write_output("#" + OUTPUT_FILE_HEADER_LINE, output_file_)
        for cost_and_usage_by_time in cost_and_usage_data:
            total_cost = 0
            for cost_group_data in cost_and_usage_by_time["Groups"]:
                cost_group = CostGroup(aws_name,
                    cost_group_data, cost_and_usage_by_time, monthly)
                write_output(str(cost_group), output_file_)
                total_cost += float(cost_group.amount)
            if enable_total:
                total_msg = "Total Cost: %s,,,,,\n" % str(total_cost)
                write_output(total_msg, output_file_)


def write_output(msg, output_file, reflect_to_stdout=True):
    if reflect_to_stdout:
        print(msg.strip())
    output_file.write(msg)


# we memoize calls to aws api to get account id, to avoid spamming it
@functools.cache
def get_account_alias(aws_client, account_id):
    try:
        result = aws_client.describe_account(AccountId=account_id).get('Account')["Name"]
    except Exception as e:
        result = account_id
    return result


class CostGroup:
    """ Class that abstracts a cost group. Will allow us to have shorter
    and more simple functions by going to the essence of the concept."""

    def __init__(self, aws_name, cost_group_data, cost_and_usage_by_time, is_monthly):
        self.account_id = get_account_alias(aws_name, cost_group_data["Keys"][0])
        self.project = cost_group_data["Keys"][1]
        self.time_start = cost_and_usage_by_time["TimePeriod"]["Start"]
        if is_monthly:
            date_parts = self.time_start.split("-")
            self.time_start = "%s/%s" % (date_parts[1], date_parts[0])
        self.amount = cost_group_data["Metrics"]["UnblendedCost"]["Amount"]
        self.unit = cost_group_data["Metrics"]["UnblendedCost"]["Unit"]
        self.estimated = cost_and_usage_by_time["Estimated"]

    def __repr__(self):
        return "%s, %s, %s, %s, %s, %s\n" % (
            self.time_start,
            self.account_id,
            self.project,
            self.amount,
            self.unit,
            self.estimated)


if __name__ == "__main__":
    main()

# AWS cost explorer report

Simple reporting tool to extract AWS cost on a daily, or monthly basis in regard
with used services.


## Running the report

### Prerequisites

You must run the tool with **python3** and [AWS SDK for Python ](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) installed. To install the SDK and ```virtualenv``` you must run ``` pip install boto3 virtualenv ```.

Your AWS account credentials must either be setup in **$HOME/.aws/credentials** file (and then you will need
to precise the profile name), or you can put the access key in the environment and then use the option **env-auth**


You can use virtualenv, or any other manager like conda. As guide for virtualenv, take a look into the following
command line example:

```
python -v virtualenv venv
source venv/bin/activate
pip install boto3

python aws-cost-and-usage-report.py
```

### Usage

By default the script will query the cloud for cost of the current month, which is equivalent with running it with **--month 1** option.

Tool's help options are the following.

```
usage: aws-cost-and-usage-report.py [-h] [--output FPATH]
                                    [--profile-name PROFILE_NAME]
                                    [--days DAYS] [--months MONTHS]
                                    [--disable-total]

AWS Simple Cost and Usage Report

optional arguments:
  -h, --help            show this help message and exit
  --output FPATH        output file path (default:report.csv)
  --profile-name PROFILE_NAME
                        Profile name on your AWS account (default:default)
  --days DAYS           get data for daily usage and cost by given days.
                        (Mutualy exclusive with 'months' option, default: 0)
  --months MONTHS       get data for monthly usage and cost by given months.
                        (Mutualy exclusive with 'days' option, default: 1)
  --env-auth            Will use AWS_ACCES_KEY_ID and AWS_SECRET_ACCESS_KEY env
                        variables to initialize the session.
  --disable-total       Do not output total cost per day, or month unit.
```

### Output

The output is dumped into a **CSV** file which you can specify by **--output** option by path.

Example of an output for costs of current month could looks like the following, where the account id hidden by **XXXXXXXXXXXX**:
```
Time Period,Organization,Project,Amount,Unit,Estimated
09/2018,XXXXXXXXXXXX,Project$,0.28,USD,True
09/2018,XXXXXXXXXXXX,Project$InternalTools,0.5888888936,USD,True
09/2018,XXXXXXXXXXXX,Project$Storage,0,USD,True
09/2018,XXXXXXXXXXXX,Project$Dadapouet,0,USD,True
Total Cost: 6.706308343800001,,,,,

```

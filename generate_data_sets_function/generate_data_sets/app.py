# import requests

from datetime import date, datetime, timezone, timedelta
from botocore.exceptions import ClientError

import boto3
import os

DAILY_REPORTS = [
    'customer_subscriber_annual_subscriptions',
    'customer_subscriber_hourly_monthly_subscriptions',
    'daily_business_canceled_product_subscribers',
    'daily_business_fees',
    'daily_business_free_trial_conversions',
    'daily_business_new_instances',
    'daily_business_new_product_subscribers',
    'daily_business_usage_by_instance_type'
]

MONTHLY_REPORTS = [
    'monthly_revenue_annual_subscriptions',
    'monthly_revenue_billing_and_revenue_data',
    'monthly_revenue_field_demonstration_usage',
    'monthly_revenue_flexible_payment_schedule',
    'sales_compensation_billed_revenue',
    'us_sales_and_use_tax_records'
]

THIRTY_DAY_REPORTS = [
    'disbursed_amount_by_product',
    'disbursed_amount_by_instance_hours',
    'disbursed_amount_by_customer_geo'
]

EXTRA_LINE_REPORTS = [
    'disbursed_amount_by_age_of_past_due_funds',
    'disbursed_amount_by_age_of_uncollected_funds',
    'disbursed_amount_by_age_of_disbursed_funds',
    'disbursed_amount_by_uncollected_funds_breakdown'
]

def generate_reports(client, published_datetime, reports,extra_line_suffix=''):
    for report in reports:
        # disbursed_amount_by_uncollected_funds_breakdown data sets are not available before 2019-10-04T00:00:00.000Z
        if report == 'disbursed_amount_by_uncollected_funds_breakdown' and published_datetime.date() < date.fromisoformat('2019-10-04'):
            continue

        print(f'Requesting {report} for {published_datetime}')

        try:
            response = client.generate_data_set(
                dataSetType=report,
                dataSetPublicationDate=published_datetime,
                roleNameArn=os.environ['ROLE_NAME'],
                destinationS3BucketName=os.environ['DESTINATION_BUCKET'],
                destinationS3Prefix=os.environ['DESTINATION_PREFIX']+extra_line_suffix,
                snsTopicArn=os.environ['SNS_TOPIC']
            )
            print(f'Response id is {response["dataSetRequestId"]}')
        except ClientError as err:
            print(err)


def generate_reports_for_date(client, published_date):
    published_datetime = datetime(published_date.year, published_date.month, published_date.day)

    generate_reports(client, published_datetime, DAILY_REPORTS)

    # Monthly reports are available on the 15th day of the month by 24:00 UTC
    if published_date.day == 15:
        generate_reports(client, published_datetime, MONTHLY_REPORTS)
    # Despite the docs, '30 day' reports seem to be published on the 10th of the month
    elif published_date.day == 10:
        generate_reports(client, published_datetime, THIRTY_DAY_REPORTS)
        generate_reports(client, published_datetime, EXTRA_LINE_REPORTS, '-extra-line')


def lambda_handler(event, context):
    """Sample Lambda function reacting to EventBridge events

    Parameters
    ----------
    event: dict, required
        Event Bridge EC2 State Change Events Format

        Event doc: https://docs.aws.amazon.com/eventbridge/latest/userguide/event-types.html#ec2-event-type

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
        The same input event file
    """
    # Region MUST be us-east-1
    client = boto3.client('marketplacecommerceanalytics', region_name='us-east-1')

    # Reports are available by 24:00 UTC, so need to ask for yesterday in UTC
    published_date = datetime.now(timezone.utc).date() - timedelta(days=1)

    generate_reports_for_date(client, published_date)

# Ad hoc report generation
#
# def daterange(start_date, end_date):
#     for n in range(int ((end_date - start_date).days)):
#         yield start_date + timedelta(n)
#
# start_date = date(2020, 3, 18)
# end_date = date(2020, 3, 25)
#
# client = boto3.client('marketplacecommerceanalytics', region_name='us-east-1')
#
# for published_date in daterange(start_date, end_date):
#     generate_reports_for_date(client, published_date)
import io
import s3fs
import boto3
import pyarrow.parquet as pq
import csv
import pandas as pd


def open_s3_resource():
    s3_resource = boto3.resource(
        's3'
    )
    return s3_resource


def open_s3fs_connection():
    s3 = s3fs.S3FileSystem()
    return s3


def dataframe_to_s3(df, bucket, key, file_type='csv'):
    s3_resource = open_s3_resource()
    if file_type == 'csv':
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, sep="|", index=False, quoting=csv.QUOTE_NONE, encoding='utf-8', escapechar='\\')
        s3_resource.Object(bucket, key).put(Body=csv_buffer.getvalue(), ACL='bucket-owner-full-control')
    elif file_type == 'parquet':
        s3 = open_s3fs_connection()
        s3_path = f'{bucket}/{key}'
        df.to_parquet(s3.open(s3_path, 'wb'))
        s3.chmod(s3_path, acl='bucket-owner-full-control')
    print('Finished Moving DataFrame to S3 {}/{}'.format(bucket, key))
    return None


def get_s3_data_to_df(bucket, key, file_type='csv', error_bad_lines=True, dtype=None):
    """
    :param bucket: The bucket to pull data from
    :param key: The key to pull data from. If CSV, do one file. If parquet, end with directory
    :param file_type: defaults to csv, but can also provide parquet
    :param error_bad_lines: Set to False if you want to skip rows that have issues
    :return: A dataframe
    """
    if file_type == 'csv':
        s3_resource = open_s3_resource()
        file = s3_resource.Object(bucket, key=key)
        df = pd.read_csv(io.BytesIO(file.get()['Body'].read()), error_bad_lines=error_bad_lines)
        if '|' in df.columns[0]:
            df = pd.read_csv(io.BytesIO(file.get()['Body'].read()), sep='|', error_bad_lines=error_bad_lines,
                             dtype=dtype)
    elif file_type == 'parquet':
        s3 = open_s3fs_connection()
        df = pq.ParquetDataset('s3://{}/{}'.format(bucket, key), filesystem=s3).read_pandas().to_pandas()
    return df
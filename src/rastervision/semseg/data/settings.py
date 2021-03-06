from os import environ
from os.path import join

data_path = '/opt/data/'
datasets_path = join(data_path, 'datasets')
results_path = join(data_path, 'results')
s3_bucket = environ.get('S3_BUCKET')

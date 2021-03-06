import os
from os import makedirs
from os.path import splitext, basename, join, isdir, dirname
import sys
import zipfile
from subprocess import call
import json

# For some reason, you need to import PIL first.
from PIL import Image
import numpy as np
import rasterio

from rastervision.common.settings import (
    s3_results_path, results_path, s3_datasets_path, datasets_path)


def _makedirs(path):
    try:
        makedirs(path)
    except:
        pass


def load_rasterio(file_path, window=None):
    with rasterio.open(file_path, 'r+') as r:
        return np.transpose(r.read(window=window), axes=[1, 2, 0])


def load_pillow(file_path, window=None):
    im = Image.open(file_path)
    if window is not None:
        ((row_begin, row_end), (col_begin, col_end)) = window
        box = (col_begin, row_begin, col_end, row_end)
        im = im.crop(box)
    im = np.array(im)
    if len(im.shape) == 2:
        im = np.expand_dims(im, axis=2)
    return im


def load_img(file_path, window=None):
    ext = splitext(file_path)[1]
    if ext in ['.tif', '.tiff']:
        return load_rasterio(file_path, window)
    return load_pillow(file_path, window)


def get_rasterio_size(file_path):
    with rasterio.open(file_path, 'r+') as r:
        nb_rows, nb_cols = r.height, r.width
        return nb_rows, nb_cols


def get_pillow_size(file_path):
    im = Image.open(file_path)
    nb_cols, nb_rows = im.size
    return nb_cols, nb_rows


def get_img_size(file_path):
    ext = splitext(file_path)[1]
    if ext in ['.tif', '.tiff']:
        return get_rasterio_size(file_path)
    return get_pillow_size(file_path)


def save_rasterio(im, file_path):
    height, width, count = im.shape
    with rasterio.open(file_path, 'w', driver='GTiff', height=height,
                       compression=rasterio.enums.Compression.none,
                       width=width, count=count, dtype=im.dtype) as dst:
        for channel_ind in range(count):
            dst.write(im[:, :, channel_ind], channel_ind + 1)


def save_pillow(im, file_path):
    im = Image.fromarray(im)
    im.save(file_path)


def save_img(im, file_path):
    ext = splitext(file_path)[1]
    if ext in ['.tif', '.tiff']:
        save_rasterio(im, file_path)
    else:
        save_pillow(im, file_path)


def save_numpy_array(file_path, arr):
    np.save(file_path, arr.astype(np.uint8))


def expand_dims(func):
    def wrapper(self, batch):
        ndim = batch.ndim
        if ndim == 3:
            batch = np.expand_dims(batch, axis=0)
        batch = func(self, batch)
        if ndim == 3:
            batch = np.squeeze(batch, axis=0)
        return batch
    return wrapper


def safe_divide(a, b):
    """
    Avoid divide by zero
    http://stackoverflow.com/questions/26248654/numpy-return-0-with-divide-by-zero
    """
    with np.errstate(divide='ignore', invalid='ignore'):
        c = np.true_divide(a, b)
        c[c == np.inf] = 0
        c = np.nan_to_num(c)
        return c


def compute_ndvi(red, ir):
    ndvi = safe_divide((ir - red), (ir + red))
    return ndvi


def get_channel_stats(batch):
    nb_channels = batch.shape[3]
    channel_data = np.reshape(
        np.transpose(batch, [3, 0, 1, 2]), (nb_channels, -1))

    means = np.mean(channel_data, axis=1)
    stds = np.std(channel_data, axis=1)
    return (means, stds)


def zip_dir(in_path, out_path):
    zipf = zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED)

    for root, dirs, files in os.walk(in_path):
        for f in files:
            zipf.write(os.path.join(root, f), basename(f))

    zipf.close()


def s3_sync(src_path, dst_path):
    call(['aws', 's3', 'sync', src_path, dst_path])


def s3_cp(src_path, dst_path):
    call(['aws', 's3', 'cp', src_path, dst_path])


def make_sync_results(run_name):
    def sync_results(download=False):
        s3_run_path = join(s3_results_path, run_name)
        run_path = join(results_path, run_name)
        if download:
            s3_sync(s3_run_path, run_path)
        else:
            s3_sync(run_path, s3_run_path)

    return sync_results


def download_dataset(dataset_path):
    src_path = join(s3_datasets_path, dataset_path)
    dst_path = join(datasets_path, dataset_path)
    s3_cp(src_path, dst_path)


def get_zip_dataset(dataset_name):
    dataset_path = join(
        datasets_path, dataset_name)
    dataset_zip_path = '{}.zip'.format(dataset_name)

    if not isdir(dataset_path):
        _makedirs(dataset_path)

        print('Downloading {}...'.format(dataset_zip_path))
        download_dataset(dataset_zip_path)

        zip_path = join(
            datasets_path, dataset_zip_path)
        dataset_path_parent = dirname(dataset_path)
        cmd = ['unzip', zip_path, '-d', dataset_path_parent]
        call(cmd)


class Logger(object):
    """Used to log stdout to a file and to the console."""

    def __init__(self, run_path):
        self.terminal = sys.stdout
        self.log = open(join(run_path, 'stdout.txt'), 'a')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        pass


def setup_run(run_path, options, sync_results):
    """Setup path for the results of a run.

    Creates directory if doesn't exist, downloads results from cloud, and
    write the options to <run_path>/options.json

    # Arguments
        run_path: the path to the files for a run
        options: RunOptions object that specifies the run
        sync_results: function used to sync results with cloud
    """
    if not isdir(run_path):
        sync_results(download=True)

    _makedirs(run_path)

    options_json = json.dumps(options.__dict__, sort_keys=True, indent=4)
    options_path = join(run_path, 'options.json')
    with open(options_path, 'w') as options_file:
        options_file.write(options_json)

    return run_path

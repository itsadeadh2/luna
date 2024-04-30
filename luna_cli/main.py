import os
import shelve
import boto3
import click
from tqdm import tqdm
from boto3.s3.transfer import S3Transfer, TransferConfig
from prettytable import PrettyTable

CONFIG_SHELVE_PATH = os.path.join(os.path.expanduser('~'), 'luna_config')


def read_config():
    """Reads the bucket name from the configuration file."""
    try:
        with shelve.open(CONFIG_SHELVE_PATH) as config_db:
            return config_db.get('bucket_name')
    except Exception as e:
        click.echo(f"Error reading configuration: {str(e)}")
        return None


def get_md5(file_path):
    """Generates an MD5 checksum for the given file."""
    import hashlib
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_size(start_path, ignore_ext):
    """Recursively calculates the total size of a directory."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            if any(f.lower().endswith(ext) for ext in ignore_ext):
                continue
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size


def list_s3_objects(bucket, s3_client):
    """List all objects in an S3 bucket along with their custom metadata."""
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket)
    objects = {}
    for page in pages:
        for obj in page.get('Contents', []):
            response = s3_client.head_object(Bucket=bucket, Key=obj['Key'])
            objects[obj['Key']] = response.get('Metadata').get('file-md5', None)
    return objects


def upload_file(transfer, file_path, bucket_name, s3_key, extra_args, progress_bar):
    """Upload a file to S3 using S3Transfer."""
    file_size = os.path.getsize(file_path)
    progress_bar.set_description(f"Uploading {os.path.basename(file_path)}")
    transfer.upload_file(file_path, bucket_name, s3_key, extra_args=extra_args)
    progress_bar.update(file_size)


def get_transfer_config():
    """Returns a custom TransferConfig."""
    return TransferConfig(
        multipart_threshold=1024 * 25,  # Set multipart threshold to 25 MB
        max_concurrency=10,  # Allow up to 10 threads
        multipart_chunksize=1024 * 25 * 1024,  # Set chunk size to 25 MB
        use_threads=True  # Enable threading
    )


@click.group()
def cli():
    """luna CLI for managing local folders and AWS S3 interactions."""
    pass


@click.command()
@click.argument('folder_path', type=click.Path(exists=True, file_okay=False))
@click.option('--ignore-ext', '-i', multiple=True, type=str, help="File extensions to ignore")
def checkfolder(folder_path, ignore_ext):
    """List all top-level files and directories in the given folder along with their sizes, ordered from biggest to smallest."""
    entries = os.listdir(folder_path)
    ignore_ext = set('.' + ext.lstrip('.').lower() for ext in ignore_ext)
    sizes = []
    with tqdm(total=len(entries), desc='Calculating sizes', unit='items') as bar:
        for entry in entries:
            full_path = os.path.join(folder_path, entry)
            if os.path.isdir(full_path):
                size = get_size(full_path, ignore_ext)
            else:
                if any(full_path.lower().endswith(ext) for ext in ignore_ext):
                    continue
                size = os.path.getsize(full_path)
            sizes.append((entry, size))
            bar.update(1)

    # Sort the list by size in descending order
    sizes.sort(key=lambda x: x[1], reverse=True)

    # Create and populate the table with sorted results
    table = PrettyTable()
    table.field_names = ["File/Directory", "Size (MB)"]
    for entry, size in sizes:
        table.add_row([entry, f"{size / (1024 ** 2):.2f}"])

    print(table)


@click.command()
@click.argument('folder_path', type=click.Path(exists=True, file_okay=False))
@click.option('--ignore-ext', '-i', multiple=True, type=str, help="File extensions to ignore")
def upload(folder_path, ignore_ext):
    """Upload the folder to the configured AWS S3 bucket while preserving the directory structure and skipping unchanged files."""
    bucket_name = read_config()
    if not bucket_name:
        click.echo("No configuration found. Please run 'luna configure'.")
        return  # Exit if no configuration is found
    session = boto3.Session()
    s3_client = session.client('s3')
    transfer = S3Transfer(s3_client, config=get_transfer_config())  # Pass the custom TransferConfig
    s3_objects = list_s3_objects(bucket_name, s3_client)  # Get all S3 objects

    files = [(dirpath, filename) for dirpath, dirs, filenames in os.walk(folder_path) for filename in filenames]
    total_size = 0
    ignore_ext = set('.' + ext.lstrip('.').lower() for ext in ignore_ext)
    with tqdm(total=len(files), desc='Calculating sizes', unit='files') as bar:
        for dirpath, filename in files:
            if any(filename.lower().endswith(ext) for ext in ignore_ext):
                continue
            file_path = os.path.join(dirpath, filename)
            total_size += os.path.getsize(file_path)
            bar.update(1)

    with tqdm(total=total_size, unit='B', unit_scale=True, desc='Uploading Folder') as bar:
        for dirpath, dirs, files in os.walk(folder_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in ignore_ext):
                    continue
                full_path = os.path.join(dirpath, file)
                relative_path = os.path.relpath(full_path, start=os.path.dirname(folder_path))
                s3_key = relative_path.replace(os.sep, '/')
                local_md5 = get_md5(full_path)
                if s3_key in s3_objects and s3_objects[s3_key].strip('"') == local_md5:
                    bar.update(os.path.getsize(full_path))
                    continue  # Skip uploading this file as it is unchanged

                extra_args = {
                    'StorageClass': 'ONEZONE_IA',
                    'Metadata': {'file-md5': local_md5}
                }
                upload_file(transfer, full_path, bucket_name, s3_key, extra_args, bar)


@click.command()
def configure():
    """Set up the default AWS bucket to use."""
    bucket_name = click.prompt("Please enter the default AWS S3 bucket name", type=str)
    try:
        with shelve.open(CONFIG_SHELVE_PATH) as config_db:
            config_db['bucket_name'] = bucket_name
        click.echo("AWS S3 bucket configuration saved.")
    except Exception as e:
        click.echo(f"Failed to save configuration: {str(e)}")


cli.add_command(checkfolder)
cli.add_command(upload)
cli.add_command(configure)

if __name__ == '__main__':
    cli()

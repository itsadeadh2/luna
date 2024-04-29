
# Luna CLI Tool

## Overview
Luna is a command-line interface (CLI) tool designed to manage the upload of folders to AWS S3 buckets efficiently by preserving the directory structure and skipping unchanged files. It utilizes Python, Boto3, and the `tqdm` library to facilitate this process.

## Features
- **Upload Management**: Upload folders to AWS S3 with directory preservation.
- **Change Detection**: Skips uploading unchanged files by comparing MD5 checksums.
- **Configuration Management**: Configures and saves AWS S3 bucket names using a local database stored in the user's home directory.

## Installation
To install Luna, you can use pip to install directly from PyPI:

```bash
pip install git+https://github.com/itsadeadh2/luna.git
```

Alternatively, if you have the source code, navigate to the directory containing `setup.py` and run:

```bash
pip install .
```

## Usage
1. **Configuration**:
   Set up the default AWS S3 bucket for uploads:
   ```bash
   luna configure
   ```

2. **Check Folder**:
   Calculate and display the size of a directory:
   ```bash
   luna checkfolder "/path/to/folder"
   ```

3. **Upload**:
   Upload a directory to the configured AWS S3 bucket:
   ```bash
   luna upload "/path/to/folder"
   ```

## Configuration
The configuration is stored using the `shelve` library in a file located in the user's home directory, ensuring easy access and management.

## Requirements
- Python 3.6+
- boto3
- click
- tqdm

## License
This project is licensed under the MIT License - see the LICENSE file for details.

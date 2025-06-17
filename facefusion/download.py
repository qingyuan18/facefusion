import os
import subprocess
from functools import lru_cache
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from tqdm import tqdm

import facefusion.choices
from facefusion import curl_builder, logger, process_manager, state_manager, wording
from facefusion.filesystem import get_file_name, get_file_size, is_file, remove_file
from facefusion.hash_helper import validate_hash
from facefusion.types import Commands, DownloadProvider, DownloadSet


def open_curl(commands : Commands) -> subprocess.Popen[bytes]:
	commands = curl_builder.run(commands)
	return subprocess.Popen(commands, stdin = subprocess.PIPE, stdout = subprocess.PIPE)


def conditional_download(download_directory_path : str, urls : List[str]) -> None:
	for url in urls:
		download_file_name = os.path.basename(urlparse(url).path)
		download_file_path = os.path.join(download_directory_path, download_file_name)
		initial_size = get_file_size(download_file_path)
		download_size = get_static_download_size(url)

		if initial_size < download_size:
			with tqdm(total = download_size, initial = initial_size, desc = wording.get('downloading'), unit = 'B', unit_scale = True, unit_divisor = 1024, ascii = ' =', disable = state_manager.get_item('log_level') in [ 'warn', 'error' ]) as progress:
				commands = curl_builder.chain(
					curl_builder.download(url, download_file_path),
					curl_builder.set_timeout(10)
				)
				open_curl(commands)
				current_size = initial_size
				progress.set_postfix(download_providers = state_manager.get_item('download_providers'), file_name = download_file_name)

				while current_size < download_size:
					if is_file(download_file_path):
						current_size = get_file_size(download_file_path)
						progress.update(current_size - progress.n)


@lru_cache(maxsize = None)
def get_static_download_size(url : str) -> int:
	commands = curl_builder.chain(
		curl_builder.head(url),
		curl_builder.set_timeout(5)
	)
	process = open_curl(commands)
	lines = reversed(process.stdout.readlines())

	for line in lines:
		__line__ = line.decode().lower()
		if 'content-length:' in __line__:
			_, content_length = __line__.split('content-length:')
			return int(content_length)

	return 0


@lru_cache(maxsize = None)
def ping_static_url(url : str) -> bool:
	commands = curl_builder.chain(
		curl_builder.head(url),
		curl_builder.set_timeout(5)
	)
	process = open_curl(commands)
	process.communicate()
	return process.returncode == 0


def conditional_download_hashes(hash_set : DownloadSet) -> bool:
	hash_paths = [ hash_set.get(hash_key).get('path') for hash_key in hash_set.keys() ]

	process_manager.check()
	_, invalid_hash_paths = validate_hash_paths(hash_paths)
	if invalid_hash_paths:
		for index in hash_set:
			if hash_set.get(index).get('path') in invalid_hash_paths:
				invalid_hash_url = hash_set.get(index).get('url')
				if invalid_hash_url:
					download_directory_path = os.path.dirname(hash_set.get(index).get('path'))
					conditional_download(download_directory_path, [ invalid_hash_url ])

	valid_hash_paths, invalid_hash_paths = validate_hash_paths(hash_paths)

	for valid_hash_path in valid_hash_paths:
		valid_hash_file_name = get_file_name(valid_hash_path)
		logger.debug(wording.get('validating_hash_succeed').format(hash_file_name = valid_hash_file_name), __name__)
	for invalid_hash_path in invalid_hash_paths:
		invalid_hash_file_name = get_file_name(invalid_hash_path)
		logger.error(wording.get('validating_hash_failed').format(hash_file_name = invalid_hash_file_name), __name__)

	if not invalid_hash_paths:
		process_manager.end()
	return not invalid_hash_paths


def conditional_download_sources(source_set : DownloadSet) -> bool:
	source_paths = [ source_set.get(source_key).get('path') for source_key in source_set.keys() ]

	process_manager.check()
	_, invalid_source_paths = validate_source_paths(source_paths)
	if invalid_source_paths:
		for index in source_set:
			if source_set.get(index).get('path') in invalid_source_paths:
				invalid_source_url = source_set.get(index).get('url')
				if invalid_source_url:
					download_directory_path = os.path.dirname(source_set.get(index).get('path'))
					conditional_download(download_directory_path, [ invalid_source_url ])

	valid_source_paths, invalid_source_paths = validate_source_paths(source_paths)

	for valid_source_path in valid_source_paths:
		valid_source_file_name = get_file_name(valid_source_path)
		logger.debug(wording.get('validating_source_succeed').format(source_file_name = valid_source_file_name), __name__)
	for invalid_source_path in invalid_source_paths:
		invalid_source_file_name = get_file_name(invalid_source_path)
		logger.error(wording.get('validating_source_failed').format(source_file_name = invalid_source_file_name), __name__)

		if remove_file(invalid_source_path):
			logger.error(wording.get('deleting_corrupt_source').format(source_file_name = invalid_source_file_name), __name__)

	if not invalid_source_paths:
		process_manager.end()
	return not invalid_source_paths


def validate_hash_paths(hash_paths : List[str]) -> Tuple[List[str], List[str]]:
	valid_hash_paths = []
	invalid_hash_paths = []

	for hash_path in hash_paths:
		if is_file(hash_path):
			valid_hash_paths.append(hash_path)
		else:
			invalid_hash_paths.append(hash_path)

	return valid_hash_paths, invalid_hash_paths


def validate_source_paths(source_paths : List[str]) -> Tuple[List[str], List[str]]:
	valid_source_paths = []
	invalid_source_paths = []

	for source_path in source_paths:
		if validate_hash(source_path):
			valid_source_paths.append(source_path)
		else:
			invalid_source_paths.append(source_path)

	return valid_source_paths, invalid_source_paths


def resolve_download_url(base_name : str, file_name : str) -> Optional[str]:
	download_providers = state_manager.get_item('download_providers')

	for download_provider in download_providers:
		download_url = resolve_download_url_by_provider(download_provider, base_name, file_name)
		if download_url:
			return download_url

	return None


def resolve_download_url_by_provider(download_provider : DownloadProvider, base_name : str, file_name : str) -> Optional[str]:
	download_provider_value = facefusion.choices.download_provider_set.get(download_provider)

	for download_provider_url in download_provider_value.get('urls'):
		if ping_static_url(download_provider_url):
			return download_provider_url + download_provider_value.get('path').format(base_name = base_name, file_name = file_name)

	return None


def is_s3_path(path: str) -> bool:
	"""Check if a path is an S3 URL."""
	return path.startswith('s3://')


def download_s3_file(s3_path: str, local_directory: str = '/tmp') -> Optional[str]:
	"""
	Download a file from S3 to local directory.
	Returns the local file path if successful, None otherwise.
	"""
	try:
		import boto3
		from botocore.exceptions import ClientError, NoCredentialsError

		# Parse S3 path
		parsed = urlparse(s3_path)
		bucket_name = parsed.netloc
		object_key = parsed.path.lstrip('/')

		if not bucket_name or not object_key:
			logger.error(f"Invalid S3 path: {s3_path}", __name__)
			return None

		# Generate local file path
		file_name = os.path.basename(object_key)
		local_file_path = os.path.join(local_directory, file_name)

		# Check if file already exists and has content
		if is_file(local_file_path) and get_file_size(local_file_path) > 0:
			logger.info(f"File already exists locally: {local_file_path}", __name__)
			return local_file_path

		# Create directory if it doesn't exist
		os.makedirs(local_directory, exist_ok=True)

		# Initialize S3 client
		s3_client = boto3.client('s3')

		# Get file size for progress bar
		try:
			response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
			file_size = response['ContentLength']
		except ClientError:
			file_size = 0

		# Download with progress bar
		with tqdm(total=file_size, desc=f'Downloading {file_name}', unit='B', unit_scale=True, unit_divisor=1024, ascii=' =', disable=state_manager.get_item('log_level') in ['warn', 'error']) as progress:
			def progress_callback(bytes_transferred):
				progress.update(bytes_transferred - progress.n)

			s3_client.download_file(
				bucket_name,
				object_key,
				local_file_path,
				Callback=progress_callback if file_size > 0 else None
			)

		logger.info(f"Successfully downloaded {s3_path} to {local_file_path}", __name__)
		return local_file_path

	except ImportError:
		logger.error("boto3 is required for S3 downloads. Install with: pip install boto3", __name__)
		return None
	except NoCredentialsError:
		logger.error("AWS credentials not found. Configure AWS credentials to download from S3.", __name__)
		return None
	except ClientError as e:
		logger.error(f"Failed to download from S3: {str(e)}", __name__)
		return None
	except Exception as e:
		logger.error(f"Unexpected error downloading from S3: {str(e)}", __name__)
		return None


def download_file_if_needed(file_path: str, local_directory: str = '/tmp') -> str:
	"""
	Download file if it's an S3 path, otherwise return the original path.
	Returns the local file path.
	"""
	if is_s3_path(file_path):
		local_path = download_s3_file(file_path, local_directory)
		if local_path:
			return local_path
		else:
			raise ValueError(f"Failed to download S3 file: {file_path}")
	return file_path

import os
from datetime import datetime
from typing import Optional

from facefusion.filesystem import get_file_extension, get_file_name


def get_step_output_path(job_id : str, step_index : int, output_path : str) -> Optional[str]:
	if output_path:
		output_directory_path, filename_part = os.path.split(output_path)
		output_file_name = get_file_name(filename_part)
		output_file_extension = get_file_extension(filename_part)

		# Handle case where output_path is a directory (ends with / or has no filename)
		if output_file_name is None:
			output_file_name = 'output'
			output_file_extension = '.mp4'  # Default extension

		return os.path.join(output_directory_path, output_file_name + '-' + job_id + '-' + str(step_index) + output_file_extension)
	return None


def suggest_job_id(job_prefix : str = 'job') -> str:
	return job_prefix + '-' + datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

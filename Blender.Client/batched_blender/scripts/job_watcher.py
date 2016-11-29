#-------------------------------------------------------------------------
#
# Azure Batch Blender Addon
#
# Copyright (c) Microsoft Corporation.  All rights reserved.
#
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the ""Software""), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#--------------------------------------------------------------------------

import time
import sys
import os
import re

import azure.storage.blob as storage
import azure.batch as batch
from azure.batch.batch_auth import SharedKeyCredentials

batch_client = None
storage_client = None

def header(header):
    header_chars = len(header)
    total_len = 50
    dashes = total_len - header_chars
    mult = int(dashes/2)
    padded = "\n\n" + mult*"-" + header + mult*"-"
    if dashes % 2 > 0:
        padded += "-"
    return padded

def _download_output(job_id, blob_name, output_path, size):
    def progress(data, total):
        try:
            percent = float(data)*100/float(size) 
            sys.stdout.write('    Downloading... {0}%\r'.format(int(percent)))
        except:
            sys.stdout.write('    Downloading... %\r')
        finally:
            sys.stdout.flush()

    print("Downloading task output: {}".format(blob_name))
    storage_client.get_blob_to_path(job_id, blob_name, output_path, progress_callback=progress)
    print("    Output download successful.\n")

def _track_completed_tasks(job_id, dwnld_dir):
    try:
        job_outputs = storage_client.list_blobs(job_id)
        for output in job_outputs:
            output_file = os.path.join(dwnld_dir, output.name)
        
            if not os.path.isfile(output_file):
                _download_output(job_id, output.name, output_file, output.properties.content_length)

    except (TypeError, AttributeError, KeyError) as exp:
        raise RuntimeError("Failed {0}".format(exp))


def _check_job_stopped(job):
    """
    Checks job for failure or completion.

    :Args:
        - job (:class:`batchapps.SubmittedJob`): an instance of the current
            SubmittedJob object.

    :Returns:
        - A boolean indicating True if the job completed, or False if still in
            progress.
    :Raises:
        - RuntimeError if the job has failed, or been cancelled.
    """

    stopped_status = [
        batch.models.JobState.disabling,
        batch.models.JobState.disabled,
        batch.models.JobState.terminating,
        batch.models.JobState.deleting
        ]
    running_status = [
        batch.models.JobState.active,
        batch.models.JobState.enabling
        ]

    try:
        if job.state in stopped_status:
            print(header("Job has stopped"))
            print("Job status: {0}".format(job.state))
            raise RuntimeError("Job is no longer running. Status: {0}".format(job.state))

        elif job.state == batch.models.JobState.completed:
            print(header("Job has completed"))
            return True

        elif job.state in running_status:
            return False

    except AttributeError as exp:
        raise RuntimeError(exp)

def track_job_progress(id, dwnld_dir):
    print("Tracking job with ID: {0}".format(id))
    try:
        job = batch_client.job.get(id)
        tasks = [t for t in batch_client.task.list(id) if t.id != "manager"]
        
        while True:
            completed_tasks = [t for t in tasks if t.state == batch.models.TaskState.completed]
            errored_tasks = [t for t in completed_tasks if t.execution_info.exit_code != 0]
            if len(tasks) == 0:
                percentage = 0
            else:
                percentage = (100 * len(completed_tasks)) / len(tasks)
            print("Running - {}%".format(percentage))
            if errored_tasks:
                print("    - Warning: some tasks have completed with a non-zero exit code.")

            _track_completed_tasks(id, dwnld_dir)
            if _check_job_stopped(job):
                return # Job complete

            time.sleep(10)
            job = batch_client.job.get(id)
            tasks = [t for t in batch_client.task.list(id)]

    except (TypeError, AttributeError) as exp:
        raise RuntimeError("Error occured: {0}".format(exp))

    except KeyboardInterrupt:
        raise RuntimeError("Monitoring aborted.")

def _authenticate():
    global batch_client, storage_client
    try:
        credentials = SharedKeyCredentials(
                os.environ['BLENDER_BATCH_ACCOUNT'],
                os.environ['BLENDER_BATCH_KEY'])
        batch_client = batch.BatchServiceClient(
            credentials, base_url=os.environ['BLENDER_BATCH_ENDPOINT'])
        storage_client = storage.BlockBlobService(
            os.environ['BLENDER_STORAGE_ACCOUNT'],
            os.environ['BLENDER_STORAGE_KEY'],
            endpoint_suffix="core.windows.net")
    except KeyError as exp:
        raise ValueError("Failed to authenticate: {0}".format(exp))

if __name__ == "__main__":
    try:
        job_id = sys.argv[1]
        download_dir = sys.argv[2]

        _authenticate() 

        EXIT_STRING = ""
        track_job_progress(job_id, download_dir)

    except (RuntimeError, ValueError) as exp:
        EXIT_STRING = exp

    except Exception as exp:
        EXIT_STRING = "An unexpected exception occurred: {0}".format(exp)

    finally:
        try:
            input = raw_input
        except NameError:
            pass
        print('\n' + str(EXIT_STRING))
        if input(header("Press 'enter' to exit")):
            sys.exit()
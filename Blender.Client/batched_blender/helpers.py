# Copyright (c) Microsoft Corporation
#
# All rights reserved.
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from __future__ import print_function
import datetime
import io
import os
import time

import bpy

import azure.batch.models as batchmodels


_STANDARD_OUT_FILE_NAME = 'stdout.txt'
_STANDARD_ERROR_FILE_NAME = 'stderr.txt'
_SAMPLES_CONFIG_FILE_NAME = 'configuration.cfg'


class TimeoutError(Exception):
    """An error which can occur if a timeout has expired.
    """
    def __init__(self, message):
        self.message = message

def decode_string(string, encoding=None):
    """Decode a string with specified encoding

    :type string: str or bytes
    :param string: string to decode
    :param str encoding: encoding of string to decode
    :rtype: str
    :return: decoded string
    """
    if isinstance(string, str):
        return string
    if encoding is None:
        encoding = 'utf-8'
    if isinstance(string, bytes):
        return string.decode(encoding)
    raise ValueError('invalid string type: {}'.format(type(string)))

def wait_for_tasks_to_complete(batch_client, job_id, timeout):
    """Waits for all the tasks in a particular job to complete.

    :param batch_client: The batch client to use.
    :type batch_client: `batchserviceclient.BatchServiceClient`
    :param str job_id: The id of the job to monitor.
    :param timeout: The maximum amount of time to wait.
    :type timeout: `datetime.timedelta`
    """
    time_to_timeout_at = datetime.datetime.now() + timeout

    while datetime.datetime.now() < time_to_timeout_at:
        print("Checking if all tasks are complete...")
        tasks = batch_client.task.list(job_id)

        incomplete_tasks = [task for task in tasks if
                            task.state != batchmodels.TaskState.completed]
        if not incomplete_tasks:
            return
        time.sleep(5)

    raise TimeoutError("Timed out waiting for tasks to complete")

def _read_stream_as_string(stream, encoding):
    """Read stream as string

    :param stream: input stream generator
    :param str encoding: The encoding of the file. The default is utf-8.
    :return: The file content.
    :rtype: str
    """
    output = io.BytesIO()
    try:
        for data in stream:
            output.write(data)
        if encoding is None:
            encoding = 'utf-8'
        return output.getvalue().decode(encoding)
    finally:
        output.close()
    raise RuntimeError('could not write data to stream or decode bytes')

def read_task_file_as_string(
        batch_client, job_id, task_id, file_name, encoding=None):
    """Reads the specified file as a string.

    :param batch_client: The batch client to use.
    :type batch_client: `batchserviceclient.BatchServiceClient`
    :param str job_id: The id of the job.
    :param str task_id: The id of the task.
    :param str file_name: The name of the file to read.
    :param str encoding: The encoding of the file. The default is utf-8.
    :return: The file content.
    :rtype: str
    """
    stream = batch_client.file.get_from_task(job_id, task_id, file_name)
    return _read_stream_as_string(stream, encoding)

def extract_percent_from_output(file_text):
    """ Return the completed percent of the task output.

    :param str file_text: The output text of a task.
    :return: The completed task percent.
    :rtype: int
    """
    s = file_text.splitlines()
    nbLines = 0
    totalStr = "";
    for line in s:
        if("Scene, Part" in line):
            nbLines+=1
            if(totalStr==""): #To be executed when the first line is reached
                i = -1;
                while(line[i].isdigit()):
                    totalStr = line[i]+totalStr
                    i-=1;
    if(nbLines>0 and totalStr != ""):
        return (nbLines * (100/float(totalStr)))/nbTasks;
    else:
        if(nbLines<=0):
            bpy.context.scene.batch_session.log.debug("helpers.get_job_percent : 0 lines")
        elif(totalStr==""):
            bpy.context.scene.batch_session.log.debug("helpers.get_job_percent : empty string totalStr")
        else:
            bpy.context.scene.batch_session.log.debug("helpers.get_job_percent : unknown problem")
        return 0

def get_task_percent(batch_client, job_id, task):
    """ Return the completed percent of the task. 
    The precise percent is only calculated if the task is being processed.

    :param batch_client: The batch client to use.
    :param str job_id: The id of the job.
    :param task: The task for which we want to get the percent.
    :return: The completed task percent.
    :rtype: int
    """
    if(task.state == batchmodels.TaskState.completed):
        return 100
    #elif(task.state == batchmodels.TaskState.active or task.state == batchmodels.TaskState.preparing):
    else:
        return 0
    #else:
    #    file_text = read_task_file_as_string(
    #            batch_client,
    #            job_id,
    #            task.id,
    #            _STANDARD_OUT_FILE_NAME,
    #            None)
    #    return extract_percent_from_output(file_text)

def get_job_percent(batch_client, job_id):
    """ Return the completed percent of the job.

    :param batch_client: The batch client to use.
    :param str job_id: The id of the job.
    :return: The completed job percent.
    :rtype: int
    """
    tasks = batch_client.task.list(job_id)
    task_ids = [task.id for task in tasks]
    percent = 0;
    if(len(task_ids) == 0): #It is one task per frame
        bpy.context.scene.batch_session.log.debug("helpers.get_job_percent : 0 tasks running")
        return -1
    for task in tasks:
        percent += get_task_percent(batch_client, job_id, task)/len(task_ids)
    return percent
import datetime
import os
import sys
import bpy
import azure.storage.blob as az_storage

try:
    job_id = os.environ["AZ_BATCH_JOB_ID"]
    task_id = os.environ["AZ_BATCH_TASK_ID"]
    storage_token = os.environ["STORAGE"]
    storage = az_storage.BlockBlobService(
        sas_token=storage_token, 
        endpoint_suffix='core.windows.net')
except KeyError as exp:
    print("Couldn't retrieve env variables")
    print(exp)
    sys.exit(1)

try:
    print("Downloading all task outputs")
    all_frames = list(storage.list_blobs(job_id, prefix="frames"))
    for frame in all_frames:
        if not os.path.exists(os.path.abspath(frame.name)):
            print("Downloading {} to {}".format(frame.name, os.path.abspath(frame.name)))
            storage.get_blob_to_path(job_id, frame.name, os.path.abspath(frame.name))
except Exception as exp:
    print("Failed to download frames")
    print(exp)
    sys.exit(2)

try:
    print("Importing sequence")
    bpy.context.scene.sequence_editor_clear()
    bpy.context.scene.sequence_editor_create()
    for index, blob in enumerate(all_frames):
        bpy.context.scene.sequence_editor.sequences.new_image(job_id, filepath=os.path.abspath(blob.name), channel=1, frame_start=index+1)
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = len(all_frames)
except Exception as exp:
    print("Failed to import sequence")
    print(exp)
    sys.exit(3)

try:
    print("Exporting video")
    bpy.context.scene.render.use_sequencer = True
    bpy.context.scene.render.image_settings.file_format = 'H264'
    bpy.context.scene.render.filepath = "//" + job_id
    output = os.path.basename(bpy.context.scene.render.frame_path())
    bpy.ops.render.render(animation=True)
    rendered_output = os.path.abspath(output)
except Exception as exp:
    print("Failed to export video")
    print(exp)
    sys.exit(4)

if not os.path.exists(rendered_output):
    print("Output file missing: {}").format(rendered_output)
    sys.exit(4)

try:
    print("Uploading output")
    storage.create_blob_from_path(job_id, "video/" + output, rendered_output)
except Exception as exp:
    print("Failed to upload output")
    print(exp)
    sys.exit(5)
sys.exit(0)

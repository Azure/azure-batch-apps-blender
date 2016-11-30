
import datetime
import glob
import os
import sys
import bpy

try:
    sys.path.append("/usr/local/lib/python3.4/site-packages")
    sys.path.append("/usr/local/lib/python3.4/dist-packages")
    sys.path.append("/usr/lib/python3.4/site-packages")
    sys.path.append("/usr/lib/python3.4/dist-packages")
    import azure.storage.blob as az_storage
except ImportError as e:
    print("Failed to import azure module")
    print(e)
    sys.exit(4)

try:
    job_id = os.environ["AZ_BATCH_JOB_ID"]
    task_id = os.environ["AZ_BATCH_TASK_ID"]
    storage_account = os.environ["STORAGE_ACCOUNT"]
    storage_key = os.environ["STORAGE_KEY"]
    storage = az_storage.BlockBlobService(
        storage_account,
        storage_key, 
        endpoint_suffix='core.windows.net')
except KeyError as exp:
    print("Couldn't retrieve env variables")
    print(exp)
    sys.exit(1)

frame = int(task_id)
bpy.context.scene.frame_current = frame
output = os.path.basename(bpy.context.scene.render.frame_path())
output = os.path.basename(bpy.context.scene.render.frame_path())
bpy.context.scene.render.filepath = "//" + output
filter_outputs = ['.blend']

try:
    if bpy.context.scene.render.engine == 'LUXRENDER_RENDER':
        print("LuxRender Job")
        filter_outputs.append('.lxs')
        samples = int(os.environ.get("HALT_SAMPLES", 3))
        bpy.context.scene.luxrender_engine.export_type = 'INT'
        bpy.context.scene.luxrender_engine.fixed_seed = False
        bpy.context.scene.luxcore_enginesettings.use_halt_samples = True
        bpy.data.scenes['Scene'].luxrender_halt.haltspp = samples
        output = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        for camera in bpy.data.cameras:
            if not hasattr(camera, 'luxrender_camera'):
                continue
            camera.luxrender_camera.luxrender_film.write_flm = True
except Exception as e:
    print("Failed to configure LuxRender")
    print(e)
    sys.exit(4)


bpy.ops.render.render(write_still=True)

rendered_output = os.path.abspath(output) + '*'
outputs = glob.glob(rendered_output)
if not outputs:
    print("Output file missing: {}").format(rendered_output)
    sys.exit(2)

try:
    failed = None
    for o in outputs:
      if os.path.isfile(o) and os.path.splitext(o)[1] not in filter_outputs:
        try:
          print("Uploading {}".format(o))
          storage.create_blob_from_path(job_id, os.path.basename(o), o)
        except Exception as e:
          print("Couldn't upload {}".format(o))
          print(e)
          failed = e
    if failed:
      raise e
except Exception as exp:
    print("Failed to upload output")
    print(exp)
    sys.exit(3)
sys.exit(0)

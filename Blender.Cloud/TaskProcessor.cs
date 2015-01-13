///--------------------------------------------------------------------------
///
/// Blender Batch Apps C# Cloud Assemblies 
/// 
/// Copyright (c) Microsoft Corporation.  All rights reserved. 
/// 
/// MIT License
/// 
/// Permission is hereby granted, free of charge, to any person obtaining a copy 
/// of this software and associated documentation files (the ""Software""), to deal 
/// in the Software without restriction, including without limitation the rights 
/// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
/// copies of the Software, and to permit persons to whom the Software is furnished 
/// to do so, subject to the following conditions:
/// 
/// The above copyright notice and this permission notice shall be included in 
/// all copies or substantial portions of the Software.
/// 
/// THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
/// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
/// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
/// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
/// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
/// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN 
/// THE SOFTWARE.
/// 
///--------------------------------------------------------------------------

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.IO;
using System.Globalization;
using System.IO.Compression;
using System.Threading.Tasks;
using System.Diagnostics;
using Blender.Cloud.Exceptions;
using Microsoft.Azure.Batch.Apps.Cloud;

namespace Blender.Cloud
{
    public class BlenderTaskProcessor : ParallelTaskProcessor
    {
        /// <summary>
        /// Path to the Blender executable
        /// </summary>
        private string RenderPath
        {
            get { return @"Blender\blender.exe"; }
        }

        /// <summary>
        /// Args with which to run Blender
        /// </summary>
        private string RenderArgs
        {
            get { return @"-b ""{0}"" -o ""{1}_####"" -F {2} -f {3} -t 0"; }
        }


        /// <summary>
        /// Executes the external process for processing the task
        /// </summary>
        /// <param name="task">The task to be processed.</param>
        /// <param name="settings">Contains information about the processing request.</param>
        /// <returns>The result of task processing.</returns>
        protected override TaskProcessResult RunExternalTaskProcess(ITask task, TaskExecutionSettings settings)
        {
            
            var taskParameters = BlenderParameters.FromTask(task);
            var initialFiles = CollectFiles(LocalStoragePath);

            if (!taskParameters.Valid)
            {
                Log.Error(taskParameters.ErrorText);
                return new TaskProcessResult
                {
                    Success = TaskProcessSuccess.PermanentFailure,
                    ProcessorOutput = "Parameter error: " + taskParameters.ErrorText,
                };
            }

            var inputFile = LocalPath(taskParameters.JobFile);
            var outputFile = LocalPath(taskParameters.Prefix);

            string externalProcessPath = ExecutablePath(RenderPath);
            string externalProcessArgs = string.Format(CultureInfo.InvariantCulture, RenderArgs, inputFile, outputFile, taskParameters.Format, task.TaskIndex);

            Log.Info("Calling '{0}' with Args '{1}' for Task '{2}' / Job '{3}' .", RenderPath, externalProcessArgs, task.TaskId, task.JobId);
            var processResult = ExecuteProcess(externalProcessPath, externalProcessArgs);

            if (processResult == null)
            {
                return new TaskProcessResult { Success = TaskProcessSuccess.RetryableFailure };
            }

            var newFiles = GetNewFiles(initialFiles, LocalStoragePath);
            var result = TaskProcessResult.FromExternalProcessResult(processResult, newFiles);

            var thumbnail = CreateThumbnail(task, newFiles);

            if (!string.IsNullOrEmpty(thumbnail))
            {
                var taskPreview = new TaskOutputFile
                {
                    FileName = thumbnail,
                    Kind = TaskOutputFileKind.Preview
                };
                result.OutputFiles.Add(taskPreview);
            }
            return result;

        }


        /// <summary>
        /// Method to execute the external processing for merging the tasks output into job output
        /// </summary>
        /// <param name="mergeTask">The merge task.</param>
        /// <param name="settings">Contains information about the processing request.</param>
        /// <returns>The job outputs resulting from the merge process.</returns>
        protected override JobResult RunExternalMergeProcess(ITask mergeTask, TaskExecutionSettings settings)
        {
            var taskParameters = BlenderParameters.FromTask(mergeTask);
            if (!taskParameters.Valid)
            {
                Log.Error(taskParameters.ErrorText);
                throw new InvalidParameterException(taskParameters.ErrorText);
            }

            var inputFilter = string.Format( CultureInfo.InvariantCulture, "{0}*", taskParameters.Prefix);
            var inputFiles = CollectFiles(LocalStoragePath, inputFilter);

            

            var outputFile = LocalPath("output.zip");
            var result = ZipOutputs(inputFiles, outputFile);
            result.PreviewFile = CreateThumbnail(mergeTask, inputFiles.ToArray());

            return result;
        }

        /// <summary>
        /// Retrieve a list of files that currently exist in a given location, according to a 
        /// given naming pattern.
        /// </summary>
        /// <param name="location">The directory to list the contents of.</param>
        /// <param name="pattern">The naming convention the returned files names adhere to.</param>
        /// <returns>A HashSet of the paths of the files in the directory.</returns>
        private static HashSet<string> CollectFiles(string location, string pattern = "*")
        {
            return new HashSet<string>(Directory.GetFiles(location, pattern));
        }

        /// <summary>
        /// Performs a difference between the current contents of a directory and a supplied file list.
        /// </summary>
        /// <param name="oldFiles">Set of file paths to compare.</param>
        /// <param name="location">Path to the directory.</param>
        /// <returns>An array of files paths in the directory that do not appear in the supplied set.</returns>
        private static string[] GetNewFiles(HashSet<string> oldFiles, string location)
        {
            var filesNow = CollectFiles(location);
            filesNow.RemoveWhere(oldFiles.Contains);
            filesNow.RemoveWhere(f => f.EndsWith(".temp"));
            filesNow.RemoveWhere(f => f.EndsWith(".stdout"));
            filesNow.RemoveWhere(f => f.EndsWith(".log"));
            filesNow.RemoveWhere(f => f.EndsWith(".xml"));

            return filesNow.ToArray();
        }

        /// <summary>
        /// Zips up a supplied list of output files.
        /// </summary>
        /// <param name="inputs">List of files to include in the zip.</param>
        /// <param name="output">The output zip file path.</param>
        /// <returns>A JobResult with the new zip assigned as OutputFile.</returns>
        private static JobResult ZipOutputs(HashSet<string> inputs, string output)
        {
            if (inputs.Count < 1)
            {
                throw new NoOutputsFoundException("No job outputs found.");
            }

            try
            {
                using (ZipArchive outputs = ZipFile.Open(output, ZipArchiveMode.Create))
                {
                    foreach (var input in inputs)
                    {
                        outputs.CreateEntryFromFile(input, Path.GetFileName(input), CompressionLevel.Optimal);
                    }
                }

                return new JobResult { OutputFile = output };
            }
            catch (Exception ex)
            {
                var error = string.Format("Failed to zip outputs: {0}", ex.ToString());
                throw new ZipException(error, ex);
            }
        }

        /// <summary>
        /// Create an image thumbnail for the task. If supplied image format is incompatible, no thumb
        /// will be created and no error thrown.
        /// </summary>
        /// <param name="task">The task that needs a thumbnail.</param>
        /// <param name="inputName">The task output from which to generate the thumbnail.</param>
        /// <returns>The path to the new thumbnail if created, else an empty string.</returns>
        protected string CreateThumbnail(ITask task, string[] inputs)
        {
            var filtered = inputs.Where(x => BlenderParameters.SupportedFormats.Contains(Path.GetExtension(x)));
            if (filtered.Count() < 1)
            {
                Log.Info("No thumbnail compatible images found.");
                return string.Empty;
            }

            var thumbInput = filtered.First();
            var thumbOutput = LocalPath(string.Format("{0}_{1}_thumbnail.png", task.JobId, task.TaskIndex));

            var thumbnailerPath = ExecutablePath(@"ImageMagick\convert.exe");
            var thumbnailerArgs = string.Format(@"""{0}"" -thumbnail 200x150> ""{1}""", thumbInput, thumbOutput);

            var processResult = ExecuteProcess(thumbnailerPath, thumbnailerArgs);

            if (processResult != null)
            {
                Log.Info("Generated thumbnail from {0} at {1}", thumbInput, thumbOutput);
                return thumbOutput;
            }

            Log.Info("No thumbnail generated");
            return string.Empty;
        }

        /// <summary>
        /// Run a, executable with a given set of arguments.
        /// </summary>
        /// <param name="exePath">Path the executable.</param>
        /// <param name="exeArgs">The command line arguments.</param>
        /// <returns>The ExternalProcessResult if run successfully, or null if an error was thrown.</returns>
        private ExternalProcessResult ExecuteProcess(string exePath, string exeArgs)
        {
            var process = new ExternalProcess
            {
                CommandPath = exePath,
                Arguments = exeArgs,
                WorkingDirectory = LocalStoragePath
            };

            try
            {
                return process.Run();
            }
            catch (ExternalProcessException ex)
            {
                string outputInfo = "No program output";
                if (!string.IsNullOrEmpty(ex.StandardError) || !string.IsNullOrEmpty(ex.StandardOutput))
                {
                    outputInfo = Environment.NewLine + "stderr: " + ex.StandardError + Environment.NewLine + "stdout: " + ex.StandardOutput;
                }

                Log.Error("Failed to invoke command {0} {1}: exit code was {2}.  {3}", ex.CommandPath, ex.Arguments, ex.ExitCode, outputInfo);
                return null;
            }
            catch (Exception ex)
            {
                Log.Error("Error in task processor: {0}", ex.ToString());
                return null;
            }

        }
    }
}

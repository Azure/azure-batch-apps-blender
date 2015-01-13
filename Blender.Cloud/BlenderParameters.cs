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
using System.Collections.ObjectModel;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Globalization;
using System.Threading.Tasks;
using Microsoft.Azure.Batch.Apps.Cloud;

namespace Blender.Cloud
{
    public abstract class BlenderParameters
    {
        public static readonly IList<String> SupportedFormats = new List<String> { ".png", ".bmp", ".jpg", ".tga", ".exr" };

        public abstract bool Valid { get; }

        public abstract int Start { get; }

        public abstract int End { get; }

        public abstract string JobFile { get; }

        public abstract string Prefix { get; }

        public abstract string Format { get; }

        public abstract string ErrorText { get; }

        public static BlenderParameters FromJob(IJob job)
        {
            var errors = new List<string>();

            int start = GetInt32Parameter(job.Parameters, "start", errors);
            int end = GetInt32Parameter(job.Parameters, "end", errors);

            string jobfile = GetStringParameter(job.Parameters, "jobfile", errors);
            string prefix = GetStringParameter(job.Parameters, "output", errors);
            string format = GetStringParameter(job.Parameters, "format", errors);

            if (errors.Any())
            {
                return new InvalidBlenderParameters(string.Join(Environment.NewLine, errors.Select(e => "* " + e)));
            }

            return new ValidBlenderParameters(start, end, jobfile, prefix, format);
        }
        public static BlenderParameters FromTask(ITask task)
        {
            var errors = new List<string>();

            string jobfile = GetStringParameter(task.Parameters, "jobfile", errors);
            string prefix = GetStringParameter(task.Parameters, "output", errors);
            string format = GetStringParameter(task.Parameters, "format", errors);

            if (errors.Any())
            {
                return new InvalidBlenderParameters(string.Join(Environment.NewLine, errors.Select(e => "* " + e)));
            }

            return new ValidBlenderParameters(jobfile, prefix, format);
        }


        private static int GetInt32Parameter(IDictionary<string,string> parameters, string parameterName, List<string> errors)
        {
            int value = 0;
            try
            {
                string text = parameters[parameterName];
                value = int.Parse(text, CultureInfo.InvariantCulture);
                if (value < 0)
                {
                    errors.Add(parameterName + " parameter is not a positive integer");
                }
            }
            catch (KeyNotFoundException)
            {
                errors.Add(parameterName + " parameter not specified");
            }
            catch (FormatException)
            {
                errors.Add(parameterName + " parameter is not a valid integer");
            }
            catch (Exception ex)
            {
                errors.Add("Unexpected error reading parameter " + parameterName + ": " + ex.Message);
            }
            return value;
        }

        private static string GetStringParameter(IDictionary<string, string> parameters, string parameterName, List<string> errors)
        {
            string text = "";
            try
            {
                text = parameters[parameterName];
            }
            catch (KeyNotFoundException)
            {
                errors.Add(parameterName + " parameter not specified");
            }
            catch (Exception ex)
            {
                errors.Add("Unexpected error reading parameter " + parameterName + ": " + ex.Message);
            }
            return text;
        }

        private class ValidBlenderParameters : BlenderParameters
        {
            private readonly int _start;
            private readonly int _end;
            private readonly string _jobfile;
            private readonly string _prefix;
            private readonly string _format;

            public ValidBlenderParameters(int start, int end, string jobfile, string prefix, string format)
            {
                _start = start;
                _end = end;
                _jobfile = jobfile;
                _prefix = prefix;
                _format = format;
            }

            public ValidBlenderParameters(string jobfile, string prefix, string format)
            {
                _jobfile = jobfile;
                _prefix = prefix;
                _format = format;
            }

            public override bool Valid
            {
                get { return true; }
            }

            public override int Start
            {
                get { return _start; }
            }

            public override int End
            {
                get { return _end; }
            }

            public override string JobFile
            {
                get { return _jobfile; }
            }

            public override string Prefix
            {
                get { return _prefix; }
            }

            public override string Format
            {
                get { return _format; }
            }

            public override string ErrorText
            {
                get { throw new InvalidOperationException("ErrorText does not apply to valid parameters"); }
            }
        }

        private class InvalidBlenderParameters : BlenderParameters
        {
            private readonly string _errorText;

            public InvalidBlenderParameters(string errorText)
            {
                _errorText = errorText;
            }

            public override bool Valid
            {
                get { return false; }
            }

            public override int Start
            {
                get { throw new InvalidOperationException("Start does not apply to invalid parameters"); }
            }

            public override int End
            {
                get { throw new InvalidOperationException("End does not apply to invalid parameters"); }
            }

            public override string JobFile
            {
                get { throw new InvalidOperationException("JobFile does not apply to invalid parameters"); }
            }

            public override string Prefix
            {
                get { throw new InvalidOperationException("Prefix does not apply to invalid parameters"); }
            }

            public override string Format
            {
                get { throw new InvalidOperationException("Format does not apply to invalid parameters"); }
            }

            public override string ErrorText
            {
                get { return _errorText; }
            }
        }
    }
}

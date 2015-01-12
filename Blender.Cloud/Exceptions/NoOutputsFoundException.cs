using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Runtime.Serialization;
using System.Threading.Tasks;

namespace Blender.Cloud.Exceptions
{
    [Serializable]
    public class NoOutputsFoundException : Exception
    {
        public NoOutputsFoundException()
        {

        }

        public NoOutputsFoundException(string message)
            : base(message)
        {

        }

        protected NoOutputsFoundException(SerializationInfo info, StreamingContext context)
            : base(info, context)
       {

       }
    }
}

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Runtime.Serialization;
using System.Threading.Tasks;

namespace Blender.Cloud.Exceptions
{
    [Serializable]
    public class InvalidParameterException : Exception
    {

        public InvalidParameterException()
        {

        }

        public InvalidParameterException(string message)
            : base(message)
        {

        }

        protected InvalidParameterException(SerializationInfo info, StreamingContext context)
            : base(info, context)
       {

       }
    }
}

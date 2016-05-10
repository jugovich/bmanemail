# Copyright (c) 2010 NORC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import codecs, hashlib

data_encode = codecs.utf_8_encode
data_decode = codecs.utf_8_decode
    
class DataIncrementalEncoder(codecs.IncrementalEncoder):
    def __init__(self, errors = 'strict'):
        codecs.IncrementalEncoder.__init__(self, errors)
        self.__digest = hashlib.sha1()
        self.__digest_start = self.__digest.copy()
        
    @property
    def digest(self):
        return self.__digest
    
    @digest.setter
    def digest(self, d):
        self.__digest = d
        self.__digest_start = d.copy()
        
    def encode(self, data, final = False):
        data, consumed = data_encode(data, self.errors)
        self.__digest.update(data)
        return data, consumed

    def reset(self):
        codecs.IncrementalEncoder.reset(self)
        self.__digest = self.__digest_start.copy()

class DataIncrementalDecoder(codecs.IncrementalDecoder):
    def __init__(self, errors = 'strict'):
        codecs.IncrementalDecoder.__init__(self, errors)
        self.__digest = hashlib.sha1()
        self.__digest_start = self.__digest.copy()
        
    @property
    def digest(self):
        return self.__digest
    
    @digest.setter
    def digest(self, d):
        self.__digest = d
        self.__digest_start = d.copy()
        
    def decode(self, data, final = False):
        self.__digest.update(data)
        return data_decode(data, self.errors)
                
    def reset(self):
        codecs.IncrementalDecoder.reset(self)
        self.__digest = self.__digest_start.copy()

class DataStreamWriter(codecs.StreamWriter):
    def __init__(self, stream, errors = 'strict'):
        codecs.StreamWriter.__init__(self, stream, errors)
        self.__digest = hashlib.sha1()
        self.__digest_start = self.__digest.copy()
        
    @property
    def digest(self):
        return self.__digest
    
    @digest.setter
    def digest(self, d):
        self.__digest = d
        self.__digest_start = d.copy()
        
    def reset(self):
        codecs.StreamWriter.reset(self)
        self.__digest = self.__digest_start.copy()

    def encode(self, data, errors = 'strict'):
        data, consumed = data_encode(data, self.errors)
        self.__digest.update(data)
        return data, consumed

class DataStreamReader(codecs.StreamReader):
    def __init__(self, errors = 'strict'):
        codecs.StreamReader.__init__(self, errors)
        self.__digest = hashlib.sha1()
        self.__digest_start = self.__digest.copy()
        
    @property
    def digest(self):
        return self.__digest
    
    @digest.setter
    def digest(self, d):
        self.__digest = d
        self.__digest_start = d.copy()
        
    def decode(self, data, final = False):
        orig_data = data
        data, consumed = data_decode(data, self.errors)
        self.__digest.update(orig_data[:consumed])
        return data, consumed
        
    def reset(self):
        codecs.StreamReader.reset(self)
        self.__digest = self.__digest_start.copy()

def search(codec):
    if codec == 'csharp-data':
        return codecs.CodecInfo(
            name = 'csharp-data',
            encode = data_encode,
            decode = data_decode,
            incrementalencoder = DataIncrementalEncoder,
            incrementaldecoder = DataIncrementalDecoder,
            streamreader = DataStreamReader,
            streamwriter = DataStreamWriter,
        )
    
codecs.register(search)

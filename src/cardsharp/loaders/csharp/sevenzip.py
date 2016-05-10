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

from __future__ import division, unicode_literals, absolute_import

from subprocess import Popen, PIPE
from threading import RLock, Condition
from datetime import datetime
import os

from ... import config

config.add_option('7zip_exe', section = 'csharp')

def _read_block(out):
    d = dict()
    while True:
        line = out.readline().strip()
        if line:
            d.update([line.split(' = ', 1)])
        else:
            return d

_active_7zip_files = dict()
_7zip_lock = RLock()
class SevenZip(object):
    def __init__(self, filename, mode = 'r'):
        self.filename = os.path.normcase(os.path.realpath(filename))
        self.__read, self.__write, mode = False, False, mode.lower()
        if mode.startswith('r'):
            self.__read, mode = True, mode[1:]

        if mode.startswith('w'):
            self.__write, mode = True, mode[1:]

        if self.__read:
            mode = mode[1:]
            if not os.path.exists(self.filename):
                raise IOError('Archive %r does not exist' % self.filename)

        if mode:
            raise IOError('Unknown file mode: %s' % mode)

        if not (self.__read or self.__write):
            raise IOException('File must be opened for reading or writing')

        self.closed = False
        self.type = '7z'
        self.proc = None
        self.flag = Condition()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __wait(self):
        if self.closed:
            return

        if _active_7zip_files.get(self.filename, None) == self:
            if self.proc and self.proc.poll() is None:
                self.proc.wait()
            return

        while True:
            waiting_on = None
            with _7zip_lock:
                if self.filename in _active_7zip_files:
                    waiting_on = _active_7zip_files[self.filename]
                    if waiting_on.closed:
                        waiting_on = None

                if waiting_on is None:
                    _active_7zip_files[self.filename] = self
                    return

            with waiting_on.flag:
                if not waiting_on.closed:
                    waiting_on.flag.wait()

    def __proc(self, args):
        self.__wait()
        if self.closed:
            raise IOError('7Zip file has been closed.')
        self.proc = Popen(args = args, bufsize = -1, stdout = PIPE, stdin = PIPE, stderr = PIPE)

    def __get_command(self, *args):
        return [config.csharp_7zip_exe] + list(args)

    def add(self, file):
        if not self.__write:
            raise IOException('Archive is not opened for writing')
        args = self.__get_command('u', self.filename, '-t' + self.type, '-si' + file)
        self.__proc(args = args)
        return self.proc.stdin

    def delete(self, file):
        if not self.__write:
            raise IOException('Archive is not opened for writing')
        args = self.__get_command('d', self.filename, file)
        self.__proc(args = args)

    def extract(self, file, read_fully = False):
        if not self.__read:
            raise IOException('Archive is not opened for reading')
        args = self.__get_command('e', self.filename, file, '-so')
        self.__proc(args = args)
        return self.proc.stdout

    def list(self):
        if not self.__read:
            raise IOException('Archive is not opened for reading')
        args = self.__get_command('l', self.filename, '-slt')
        self.__proc(args = args)
        out = self.proc.stdout

        out.readline()
        copyright = out.readline().strip()
        out.readline()
        archive_name = out.readline().strip()
        for x in xrange(8):
            out.readline()

        files = []
        while True:
            block = _read_block(out)
            if block:
                info = dict()
                info['filename'] = block['Path']
                if '\\' in info['filename']:
                    info['path'], info['filename'] = info['filename'].split('\\', 1)
                info['size'] = block['Size']
                info['crc'] = block['CRC']
                info['modified_date'] = datetime.strptime(block['Modified'], '%Y-%m-%d %H:%M:%S')
                files.append(info)
            else:
                break

        out.close()
        return files

    def cancel(self):
        if self.proc and self.proc.poll() is None:
            import win32api
            PROCESS_TERMINATE = 1
            handle = win32api.OpenProcess(PROCESS_TERMINATE, False, self.proc.pid)
            win32api.TerminateProcess(handle, -1)
            win32api.CloseHandle(handle)

        self.proc = None
        self.close()

    def close(self):
        try:
            if self.proc:
                self.proc.stdin.close()
                self.proc.stdout.close()
                self.proc.stderr.close()
                self.proc.wait()
                self.proc = None
        finally:
            with self.flag:
                self.closed = True
                self.flag.notifyAll()



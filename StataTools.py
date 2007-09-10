from struct import unpack, calcsize

from StataTypes import MissingValue, Variable

class Reader(object):
    """.dta file reader"""

    _header = {}
    _data_location = 0
    _col_sizes = ()
    _has_string_data = False
    _missing_values = False
    TYPE_MAP = range(251)+list('bhlfd')
    MISSING_VALUES = { 'b': (-127,100), 'h': (-32767, 32740), 'l': (-2147483647, 2147483620), 'f': (-1.701e+38, +1.701e+38), 'd': (-1.798e+308, +8.988e+307) }

    def __init__(self, file_object, missing_values=False):
        """Creates a new parser from a file object.
        
        If missing_values, parse missing values and return as a MissingValue
        object (instead of None)."""
        self._missing_values = missing_values
        self._parse_header(file_object)

    def file_headers(self):
        """Returns all .dta file headers."""
        return self._header

    def file_format(self):
        """Returns the file format.
        
        Format 113: Stata 9
        Format 114: Stata 10"""
        return self._header['ds_format']

    def file_label(self):
        """Returns the dataset's label."""
        return self._header['data_label']

    def file_timestamp(self):
        """Returns the date and time Stata recorded on last file save."""
        return self._header['time_stamp']

    def variables(self):
        """Returns a list of the dataset's PyDTA.Variables."""
        return map(Variable, zip(range(self._header['nvar']),
            self._header['typlist'], self._header['varlist'], self._header['srtlist'],
            self._header['fmtlist'], self._header['lbllist'], self._header['vlblist']))

    def dataset(self, as_dict=False):
        """Returns a Python generator object for iterating over the dataset.
        
        Each observation is returned as a list unless as_dict is set.
        Observations with a MissingValue(s) are not filtered and should be
        handled by your applcation."""
        try:
            self._file.seek(self._data_location)
        except Exception:
            pass

        if as_dict:
            vars = map(str, self.variables())
            for i in range(len(self)):
                yield dict(zip(vars, self._next()))
        else:
            for i in range(self._header['nobs']):
                yield self._next()

    ### Python special methods

    def __len__(self):
        """Return the number of observations in the dataset.

        This value is taken directly from the header and includes observations
        with missing values."""
        return self._header['nobs']

    def __getitem__(self, k):
        """Seek to an observation indexed k in the file and return it, ordered
        by Stata's output to the .dta file.

        k is zero-indexed.  Prefer using R.data() for performance."""
        if not (type(k) is int or type(k) is long) or k < 0 or k > len(self)-1:
            raise IndexError(k)
        loc = self._data_location + sum(self._col_size()) * k
        if self._file.tell() != loc:
            self._file.seek(loc)
        return self._next()

    ### PyDTA private methods

    def _null_terminate(self, s):
        try:
            return s.lstrip('\x00')[:s.index('\x00')]
        except Exception:
            return s

    def _parse_header(self, file_object):
        self._file = file_object

        # parse headers
        self._header['ds_format'] = unpack('b', self._file.read(1))[0]
        byteorder = self._header['byteorder'] = unpack('b', self._file.read(1))[0]==0x1 and '>' or '<'
        self._header['filetype'] = unpack('b', self._file.read(1))[0]
        self._file.read(1)
        nvar = self._header['nvar'] = unpack(byteorder+'h', self._file.read(2))[0]
        if self._header['ds_format'] < 114:
            self._header['nobs'] = unpack(byteorder+'i', self._file.read(4))[0]
        else:
            self._header['nobs'] = unpack(byteorder+'i', self._file.read(4))[0]
        self._header['data_label'] = self._null_terminate(self._file.read(81))
        self._header['time_stamp'] = self._null_terminate(self._file.read(18))

        # parse descriptors
        self._header['typlist'] = [self.TYPE_MAP[ord(self._file.read(1))] for i in range(nvar)]
        self._header['varlist'] = [self._null_terminate(self._file.read(33)) for i in range(nvar)]
        self._header['srtlist'] = unpack(byteorder+('h'*(nvar+1)), self._file.read(2*(nvar+1)))[:-1]
        if self._header['ds_format'] <= 113:
            self._header['fmtlist'] = [self._null_terminate(self._file.read(12)) for i in range(nvar)]
        else:
            self._header['fmtlist'] = [self._null_terminate(self._file.read(49)) for i in range(nvar)]
        self._header['lbllist'] = [self._null_terminate(self._file.read(33)) for i in range(nvar)]
        self._header['vlblist'] = [self._null_terminate(self._file.read(81)) for i in range(nvar)]

        # ignore expansion fields
        while True:
            data_type = unpack(byteorder+'b', self._file.read(1))[0]
            data_len = unpack(byteorder+'i', self._file.read(4))[0]
            if data_type == 0:
                break
            self._file.read(data_len)

        # other state vars
        self._data_location = self._file.tell()
        self._has_string_data = len(filter(lambda x: type(x) is int, self._header['typlist'])) > 0
        self._col_size()

    def _calcsize(self, fmt):
        return type(fmt) is int and fmt or calcsize(self._header['byteorder']+fmt)

    def _col_size(self, k = None):
        """Calculate size of a data record."""
        if len(self._col_sizes) == 0:
            self._col_sizes = map(lambda x: self._calcsize(x), self._header['typlist'])
        if k == None:
            return self._col_sizes
        else:
            return self._col_sizes[k]

    def _unpack(self, fmt, byt):
        d = unpack(self._header['byteorder']+fmt, byt)[0]
        if fmt[-1] in self.MISSING_VALUES:
            nmin, nmax = self.MISSING_VALUES[fmt[-1]]
            if d < nmin or d > nmax:
                if self._missing_values:
                    return MissingValue(nmax, d)
                else:
                    return None
        return d

    def _next(self):
        typlist = self._header['typlist']
        if self._has_string_data:
            data = [None]*self._header['nvar']
            for i in range(len(data)):
                if type(typlist[i]) is int:
                    data[i] = self._null_terminate(self._file.read(typlist[i]))
                else:
                    data[i] = self._unpack(typlist[i], self._file.read(self._col_size(i)))
            return data
        else:
            return map(lambda i: self._unpack(typlist[i], self._file.read(self._col_size(i))), range(self._header['nvar']))

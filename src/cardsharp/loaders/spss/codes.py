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

messages = dict()

def _catalog(category, **kw):
    messages[category] = dict()
    for v, value in kw.iteritems():
        if not isinstance(value, tuple):
            value = (value, v)
            
        messages[category][value[0]] = value[1]
        globals()[v] = value[0]

# Missing Values
_catalog('missing', 
    SPSS_NO_MISSVAL = 0,
    SPSS_ONE_MISSVAL = 1,
    SPSS_TWO_MISSVAL = 2,
    SPSS_THREE_MISSVAL = 3,
    SPSS_MISS_RANGE = -2,
    SPSS_MISS_RANGEANDVAL = -3,
)
    
# Errors and warnings
_catalog('errors', 
    SPSS_OK = 0,
    SPSS_FILE_OERROR = (1, 'Error opening file'),
    SPSS_FILE_WERROR = (2, 'Error writing file'),
    SPSS_FILE_RERROR = (3, 'Error reading file'),
    SPSS_FITAB_FULL = (4, 'File table full (too many open SPSS data files'),
    SPSS_INVALID_HANDLE = (5, 'The file handle is not valid'),
    SPSS_INVALID_FILE = (6, 'File is not a valid SPSS file'),
    SPSS_NO_MEMORY = (7, 'Insufficient memory'),
    
    SPSS_OPEN_RDMODE = (8, 'File is open for reading, not writing'),
    SPSS_OPEN_WRMODE = (9, 'File is open for writing, not reading'),
    
    SPSS_INVALID_VARNAME = (10, 'The variable name is not valid'),
    SPSS_DICT_EMPTY = 11,
    SPSS_VAR_NOTFOUND = (12, 'A variable with the given name does not exist'),
    SPSS_DUP_VAR = 13,
    SPSS_NUME_EXP = (14, 'Variable associated with this handle is not numeric'),
    SPSS_STR_EXP = (15, 'Variable associated with this handle is numeric'),
    SPSS_SHORTSTR_EXP = 16,
    SPSS_INVALID_VARTYPE = (17, 'Invalid variable type'),
    
    SPSS_INVALID_MISSFOR = 18,
    SPSS_INVALID_COMPSW = (19, 'Invalid compression switch'),
    SPSS_INVALID_PRFOR = (20, 'Invalid print format'),
    SPSS_INVALID_WRFOR = (21, 'Invalid write format'),
    SPSS_INVALID_DATE = (22, 'Invalid date'),
    SPSS_INVALID_TIME = (23, 'Invalid time'),
    
    SPSS_NO_VARIABLES = 24,
    SPSS_DUP_VALUE = 27,
    
    SPSS_INVALID_CASEWGT = 28,
    SPSS_DICT_COMMIT = (30, 'Dictionary of the output file has already been written'),
    SPSS_DICT_NOTCOMMIT = (31, 'Dictionary of the output file has not yet been written with spssCommitHeader'),
    
    SPSS_NO_TYPE2 = (33, 'File is not a valid SPSS file (no type 2 record)'),
    SPSS_NO_TYPE73 = 41,
    SPSS_INVALID_DATEINFO = 45,
    SPSS_NO_TYPE999 = (46, 'File is not a valid SPSS file (missing type 999 record)'),
    SPSS_EXC_STRVALUE = (47, 'The value is longer than the length of the variable'),
    SPSS_CANNOT_FREE = 48,
    SPSS_BUFFER_SHORT = 49,
    SPSS_INVALID_CASE = 50,
    SPSS_INTERNAL_VLABS = 51,
    SPSS_INCOMPAT_APPEND = 52,
    SPSS_INTERNAL_D_A = 53,
    SPSS_FILE_BADTEMP = 54,
    SPSS_DEW_NOFIRST = 55,
    SPSS_INVALID_MEASURELEVEL = 56,
    SPSS_INVALID_7SUBTYPE = 57,
    SPSS_INVALID_VARHANDLE = 58,
    
    SPSS_INVALID_MRSETDEF = 70,
    SPSS_INVALID_MRSETNAME = 71,
    SPSS_DUP_MRSETNAME = 72,
    
    SPSS_BAD_EXTENSION = 73,
    SPSS_INVALID_EXTENDEDSTRING = 74,
    
    SPSS_INVALID_ATTRNAME = 75,
    SPSS_INVALID_ATTRDEF = 76,
    SPSS_INVALID_MRSETINDEX = 77,
 
    # Warnings
    SPSS_EXC_LEN64 = -1,
    SPSS_EXC_LEN120 = -2,
    SPSS_EXC_VARLABEL = -2,
    SPSS_EXC_LEN60 = -4,
    SPSS_EXC_VALLABEL = -4,
    SPSS_FILE_END = (-5, 'There are no more records in the SPSS file'),
    SPSS_NO_VARSETS = -6,
    SPSS_EMPTY_VARSETS = -7,
    SPSS_NO_LABELS = -8,
    SPSS_NO_LABEL = (-9, 'The variable does not have a label'),
    SPSS_NO_CASEWGT = -10,
    SPSS_NO_DATEINFO = -11,
    SPSS_NO_MULTRESP = -12,
    SPSS_EMPTY_MULTRESP = -13,
    SPSS_NO_DEW = -14,
    SPSS_EMPTY_DEW = -15,
)
    
# Formats
_catalog('formats',     
    SPSS_FMT_A = (1, 'Alphanumeric'),
    SPSS_FMT_AHEX = (2, 'Alphanumeric hexadecimal'),
    SPSS_FMT_COMMA = (3, 'F Format with commas'),
    SPSS_FMT_DOLLAR = (4, 'Commas and floating dollar sign'),
    SPSS_FMT_F = (5, 'Default Numeric Format'),
    SPSS_FMT_IB = (6, 'Integer binary'),
    SPSS_FMT_PIBHEX = (7, 'Positive integer binary - hex'),
    SPSS_FMT_P = (8, 'Packed decimal'),
    SPSS_FMT_PIB = (9, 'Positive integer binary unsigned'),
    SPSS_FMT_PK = (10, 'Positive integer binary unsigned'),
    SPSS_FMT_RB = (11, 'Floating point binary'),
    SPSS_FMT_RBHEX = (12, 'Floating point binary hex'),
    SPSS_FMT_Z = (15, 'Zoned decimal'),
    SPSS_FMT_N = (16, 'N Format- unsigned with leading 0s'),
    SPSS_FMT_E = (17, 'E Format- with explicit power of 10'),
    SPSS_FMT_DATE = (20, 'Date format dd-mmm-yyyy'),
    SPSS_FMT_TIME = (21, 'Time format hh:mm:ss.s'),
    SPSS_FMT_DATE_TIME = (22, 'Date and Time'),
    SPSS_FMT_ADATE = (23, 'Date format mm/dd/yyyy'),
    SPSS_FMT_JDATE = (24, 'Julian date - yyyyddd'),
    SPSS_FMT_DTIME = (25, 'Date-time dd hh:mm:ss.s'),
    SPSS_FMT_WKDAY = (26, 'Day of the week'),
    SPSS_FMT_MONTH = (27, 'Month'),
    SPSS_FMT_MOYR = (28, 'mmm yyyy'),
    SPSS_FMT_QYR = (29, 'q Q yyyy'),
    SPSS_FMT_WKYR = (30, 'ww WK yyyy'),
    SPSS_FMT_PCT = (31, 'Percent - F followed by %'),
    SPSS_FMT_DOT = (32, 'Like COMMA, switching dot for comma'),
    SPSS_FMT_CCA = (33, 'User Programmable currency format (A)'),
    SPSS_FMT_CCB = (34, 'User Programmable currency format (B)'),
    SPSS_FMT_CCC = (35, 'User Programmable currency format (C)'),
    SPSS_FMT_CCD = (36, 'User Programmable currency format (D)'),
    SPSS_FMT_CCE = (37, 'User Programmable currency format (E)'),
    SPSS_FMT_EDATE = (38, 'Date in dd.mm.yyyy style'),
    SPSS_FMT_SDATE = (39, 'Date in yyyy/mm/dd style'),
)
    
# Measurement levels
_catalog('levels',     
    SPSS_MLVL_UNK = (0, 'Unknown'),
    SPSS_MLVL_NOM = (1, 'Nominal'),
    SPSS_MLVL_ORD = (2, 'Ordinal'),
    SPSS_MLVL_RAT = (3, 'Scale (Ratio),'),
)
    
# Alignment
_catalog('alignment',     
    SPSS_ALIGN_LEFT = 0,
    SPSS_ALIGN_RIGHT = 1,
    SPSS_ALIGN_CENTER = 2,
)
    
# Variable name diagnostics
_catalog('name', 
    SPSS_NAME_OK = (0, 'Valid standard name'),
    SPSS_NAME_SCRATCH = (1, 'Valid scratch var name'),
    SPSS_NAME_SYSTEM = (2, 'Valid system var name'),
    SPSS_NAME_BADLTH = (3, 'Empty or longer than SPSS_MAX_VARNAME'),
    SPSS_NAME_BADCHAR = (4, 'Invalid character or imbedded blank'),
    SPSS_NAME_RESERVED = (5, 'Name is a reserved word'),
    SPSS_NAME_BADFIRST = (6, 'Invalid initial character'),
)
    
SPSS_MAX_VARNAME = 64        # Variable name
SPSS_MAX_SHORTVARNAME = 8    # Short (compatibility), variable name
SPSS_MAX_SHORTSTRING = 8     # Short string variable
SPSS_MAX_IDSTRING = 64       # File label string
SPSS_MAX_LONGSTRING = 32767  # Long string variable
SPSS_MAX_VALLABEL = 120      # Value label
SPSS_MAX_VARLABEL = 256      # Variable label
SPSS_MAX_7SUBTYPE = 32       # Maximum record 7 subtype 

# Subtypes
_catalog('t7',  
    SPSS_T7_DOCUMENTS = (0, 'Documents (actually type 6),'),
    SPSS_T7_VAXDE_DICT = (1, 'VAX Data Entry - dictionary version'),
    SPSS_T7_VAXDE_DATA = (2, 'VAX Data Entry - data'),
    SPSS_T7_SOURCE = (3, 'Source system characteristics'),
    SPSS_T7_HARDCONST = (4, 'Source system floating pt constants'),
    SPSS_T7_VARSETS = (5, 'Variable sets'),
    SPSS_T7_TRENDS = (6, 'Trends date information'),
    SPSS_T7_MULTRESP = (7, 'Multiple response groups'),
    SPSS_T7_DEW_DATA = (8, 'Windows Data Entry data'),
    SPSS_T7_TEXTSMART = (10, 'TextSmart data'),
    SPSS_T7_MSMTLEVEL = (11, 'Msmt level, col width, & alignment'),
    SPSS_T7_DEW_GUID = (12, 'Windows Data Entry GUID'),
    SPSS_T7_XVARNAMES = (13, 'Extended variable names'),
    SPSS_T7_XSTRINGS = (14, 'Extended strings'),
    SPSS_T7_CLEMENTINE = (15, 'Clementine Metadata'),
    SPSS_T7_NCASES = (16, '64 bit N of cases'),
    SPSS_T7_FILE_ATTR = (17, 'File level attributes'),
    SPSS_T7_VAR_ATTR = (18, 'Variable attributes'),
)

# Encoding
_catalog('encoding',
    SPSS_ENCODING_CODEPAGE = 0,
    SPSS_ENCODING_UTF8 = 1,
)
PyDTA
=====

A Python library for interacting with Stata .dta files using native Python types.  PyDTA constructs Python lists with observations' variable data and objects with variables' types and labels.

This software is free and available under the [MIT license](http://joe.mit-license.org/).

# Overview

* manipulate Stata datasets in your own Python programs
* convert datasets to new Python-supported file formats or relational databases (eg. MySQL)
* perform calculations on the dataset using Python or [SciPy](http://www.scipy.org)

# Features

* multiple dataset accessors:
 * implements Python generator (`for x in DTA.dataset(): print x`)
 * implements Python `__getitem__` for dataset slicing (`print DTA[443]`)
* versions of Stata supported:
 * Stata 10 (format-114 datasets)
 * Stata 9 (format-113 datasets)
* supports all Stata string and numeric types:
 * str, byte, int, long, float, and double are converted to native Python base types
* supports other fields:
 * dataset label
 * date/time dataset written (in Stata, not OS)
 * variables' names, sort order, formats, labels, and value formats
* supports [missing values](http://www.stata.com/help.cgi?missing+values)
* supports large datasets (streaming, direct I/O)

# Examples
Note: these examples lack important attributes of well designed, production code and are intended only to demonstrate PyDTA usage syntax.

## export to CSV
    # csv_export.py
    import PyDTA, sys
    dta = PyDTA.Reader(file(sys.argv[1]))
    for observation in dta.dataset():
        print ",".join(map(str,observation))

    $ ./csv_export.py my_dataset.dta > my_dataset.csv

## export to MySQL
    import MySQLdb, PyDTA
    dta = PyDTA.Reader(file('input.dta'))
    fields = ','.join(['%s']*len(dta.variables()))
    cursor = MySQLdb.connect('localhost',db='test').cursor()
    for observation in dta.dataset():
        cursor.execute(
            'INSERT INTO test VALUES (%s)' % fields,
            map(str, observation)
        )

# Release Notes

## Discarded Fields
The current version discards value labels and Stata expansion fields.  Stata deems its expansion fields unnecessary:

"Expansion fields are used to record information that is unique to Stata and has no equivalent in other data management packages.  Expansion fields are always optional when writing data and, generally, programs reading Stata datasets will want to ignore the expansion fields." via [stata.com](http://www.stata.com/help.cgi?dta#expansion_fields)

These choices were made to improve efficiency and could be reconsidered in a later version.  Most users will not be affected.

## Missing Values

PyDTA converts and includes observations with missing values in all dataset accessors.  By default, missing values are returned as Python: `None`.  Users should be careful to ignore these observations in most scenarios.

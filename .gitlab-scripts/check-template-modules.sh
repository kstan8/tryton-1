#!/bin/sh
set -eu

OUTPUT=`mktemp -d`
find modules -name setup.py -print | while read path
do
    path=`dirname "${path}"`
    module=`basename "${path}"`
    printf "Check $module ... "
    cookiecutter --no-input cookiecutter-module -o "${OUTPUT}" module_name="${module}"
    for file in tox.ini .readthedocs.yaml doc/conf.py doc/requirements-doc.txt
    do
        cmp "${path}/${file}" "${OUTPUT}/${module}/${file}"
    done
    printf "OK\n"
done

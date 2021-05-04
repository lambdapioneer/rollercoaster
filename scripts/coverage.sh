#!/bin/bash
coverage3 run --source=simulation -m unittest -v && coverage3 report && coverage3 html -d tests/htmlcov
#echo "Run 'firefox tests/htmlcov/index.html' to display detailed results"

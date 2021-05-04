#!/bin/bash
find simulation -type d -name __pycache__ -exec rm -r {} \; 2>/dev/null;
find tests -type d -name __pycache__ -exec rm -r {} \; 2>/dev/null;
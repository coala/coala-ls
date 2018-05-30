#!/bin/sh

cd "$(dirname "$0")" > /dev/null
exec python3 -m coalals
cd - /dev/null

#!/bin/sh
# Evidence that catalogue.data.govt.nz resource URLs sit behind an Incapsula
# bot wall for plain HTTP clients (recorded 2026-11-04).
# curl -A "scout-discovery/1.0" -o fenz-metadata-2026_01.pdf "<metadata-pdf-url>"
# -> 5,996 bytes (challenge interstitial), sha256 5c380a6c881a5fa812cf1f1bb4c36b98...
# The same URL returns 1,337,658 bytes inside the supported browser session.
# The catalogue CKAN API (package_show) is likewise browser-only from here.

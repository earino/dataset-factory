#!/bin/sh
# Scheduled entrypoint. The implementation is versioned in the factory repository.
# NOTE: the scheduler runs .py scripts as Python and .sh scripts via bash, so this shim must
# keep the .sh extension - naming it .py was a SyntaxError on every tick.
exec python3 /opt/data/dataset-factory/scripts/scout-job-watch.py "$@"

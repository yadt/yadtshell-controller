#!/bin/bash
# For backward compatibility:
# Wrapper script for new yadtshell-controller script, issues
# deprecation warning and calls new script

NEWSCRIPT=yadtshell-controller

exec 3>&1 1>&2
echo
echo "WARNING: $0 is deprecated!"
echo "WARNING: Consider using $NEWSCRIPT (without the '.py') instead!"
echo

exec 1>&3
$(dirname $0)/$NEWSCRIPT $@

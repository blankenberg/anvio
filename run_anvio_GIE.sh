#!/bin/sh


anvi_command="anvi-interactive --port 80"
if [ -f /input/profile_db/PROFILE.db ]
then
    anvi_command="$anvi_command -p /input/profile_db/PROFILE.db"
fi

if [ -f /input/contig_db/CONTIGS.db ]
then
    anvi_command="$anvi_command -c /input/contig_db/CONTIGS.db"
fi

##anvi-interactive --port 80 -p /input/profile_db/PROFILE.db -c /input/contigs_db/CONTIGS.db
echo "Running $anvi_command"
$anvi_command

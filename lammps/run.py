# coding: utf-8
# Standard Python libraries
import os
import glob
import shutil
import subprocess as sp

# atomman imports
from . import Log, LammpsError

def run(lammps_command, script_name, mpi_command=None,
        restart_script_name=None, logfile='log.lammps'):
    """
    Calls LAMMPS to run. Returns data model containing LAMMPS output.
    
    Parameters
    ----------
    lammps_command : str
        The LAMMPS inline run command (sans -in script_name).
    script_name : str
        Path of the LAMMPS input script to use.
    mpi_command : str or None, optional
        The MPI inline command to run LAMMPS in parallel. Default value is 
        None (no mpi).
    restart_script_name : str or None, optional
        Alternative script to use for restarting if logfile already exists.
        Default value is None (no restarting).
    logfile : str, optional
        Specifies the path to the logfile to write to.  Default value is
        'log.lammps'.
    
    Returns
    -------
    atomman.lammps.Log or DataModelDict
        The content either as a Log object or in data model format.
    """
    
    # Check if restart_script_name is given
    if restart_script_name is not None:
        
        # Check if simulation was previously started by looking for log.lammps
        if os.path.isfile(logfile):
            logname, logext = os.path.splitext(logfile)
            # Replace script_name with restart_script_name
            script_name = restart_script_name
            
            # Search for any earlier log files with the name log-*.lammps
            logids = []
            for oldlog in glob.iglob(logname + '-*' + logext):
                logids.append(int(os.path.splitext(os.path.basename(oldlog))[0][len(logname)+1:]))
            
            # Rename old logfile to keep it from being overwritten
            if len(logids) == 0:
                lognum = 1
            else:
                lognum = max(logids)+1
            shutil.move(logfile, logname + '-' + str(lognum) + logext)
        else:
            lognum = 0
    else:
        lognum = 0
    
    # Convert lammps_command into list of terms
    if isinstance(lammps_command, str):
        lammps_command = lammps_command.split(' ')
    elif not isinstance(lammps_command, list):
        lammps_command = [lammps_command]
    
    # Convert script_name into list of terms
    if isinstance(script_name, str):
        script_name = script_name.split(' ')
    elif not isinstance(script_name, list):
        script_name = [script_name]
    
    # Convert mpi_command into list of terms
    if mpi_command is None:
        mpi_command = []
    elif isinstance(mpi_command, str):
        mpi_command = mpi_command.split(' ')
    elif not isinstance(mpi_command, list):
        mpi_command = [mpi_command]
    
    # Extra terms
    extra = []
    
    # Check if logfile is not log.lammps
    if logfile != 'log.lammps':
        # Convert logfile into list of terms
        extra += ['-log'] + logfile.split(' ')
    
    # Try to run lammps as a subprocess
    try:
        output = sp.check_output(mpi_command + lammps_command + extra + ['-in'] + script_name)
    
    # Convert LAMMPS error to a Python error if failed
    except sp.CalledProcessError as e:
        raise LammpsError(e.output.decode('UTF-8'))
    
    # Initialize Log object
    log = Log()
    
    # Read in from all old log files
    for i in range(1, lognum+1):
        log.read(logname + '-' + str(i) + logext)
    
    # Read in from current logfile
    log.read(logfile)
    
    return log
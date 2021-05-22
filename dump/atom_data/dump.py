# coding: utf-8
# Standard Python libraries
from io import open
from collections import OrderedDict
from copy import deepcopy

# http://www.numpy.org/
import numpy as np

# atomman imports
import atomman.unitconvert as uc
from .atoms_prop_info import atoms_prop_info
from .velocities_prop_info import velocities_prop_info
from ...lammps import style
from .. import dump_table

def dump(system, f=None, atom_style=None, units=None, natypes=None,
         potential=None, float_format='%.13f', return_info=True,
         return_pair_info=False, safecopy=False):
    """
    Write a LAMMPS-style atom data file from a System.
    
    Parameters
    ----------
    system : atomman.System 
        The system to write to the atom data file.
    f : str or file-like object, optional
        File path or file-like object to write the content to.  If not given,
        then the content is returned as a str.
    atom_style : str, optional
        The LAMMPS atom_style option associated with the data file.  If neither
        atom_style or potential is given, will set atom_style to 'atomic'.
    units : str, optional
        The LAMMPS units option associated with the data file.  If neither
        units or potential is given, will set units 'metal'.
    natypes : int, optional
        Allows the natypes value to be manually changed.  This is needed if
        natypes needs to be greater than the current number of atypes.  If
        neither natypes or potential is given, will use system.natypes.
    potential : atomman.lammps.Potential, optional
        Potential-specific values of atom_style, units, and natypes can be
        extracted from a Potential object.  If both potential and any of the
        individual values are given, the individual values will be used.
    float_format : str, optional
        c-style formatting string for floating point values.  Default value is
        '%.13f'.
    return_info : bool, optional
        Indicates if the LAMMPS command lines associated with reading in the
        file are to be returned as a str.  Default value is True.
    return_pair_info : bool, optional
        Indicates if the LAMMPS command lines associated with setting mass,
        pair_style and pair_coeff are included in the returned info.  If True,
        potential must be given and return_info must be True.  Default value is
        False.
    safecopy : bool, optional
        The LAMMPS data format requires all atoms to be inside box bounds, i.e.
        "wrapped".  If safecopy is True then a copy of the system is made to
        keep the original unwrapped.  Default value is False.
    
    Returns
    -------
    content : str
        The data file contents.  Returned if f is not given.
    read_info : str
        The LAMMPS input command lines to read the created data file in.
        Returned if return_info is True.  If return_pair_info is also True and
        potential is given, the LAMMPS input command lines for the potential
        are also included.

    Raises
    ------
    ValueError
        If return_pair_info is True and return_info is False or potential is
        not given.
    """
    # Wrap atoms and get imageflags
    if safecopy:
        system = deepcopy(system)
    imageflags = system.wrap(return_imageflags=True)
    
    # Extract potential-based parameters
    if potential is not None:
        if units is None:
            units = potential.units
        if atom_style is None:
            atom_style = potential.atom_style
        if natypes is None:
            natypes = len(potential.normalize_symbols(system.symbols))
    
    # Set default parameter values
    else:
        if units is None:
            units = 'metal'
        if atom_style is None:
            atom_style = 'atomic'
        if natypes is None:
            natypes = system.natypes

    # Generate header info
    content = '\n%i atoms\n' % system.natoms
    content += '%i atom types\n' % natypes
    
    # Write box content
    content += box_content(system, units, float_format)

    # Write atom info
    content += atoms_content(system, imageflags, atom_style, units, float_format)
    
    # Handle velocity information if included
    if 'velocity' in system.atoms_prop():
        
        # Write velocity info
        content += '\nVelocities\n\n'
        prop_info = velocities_prop_info(atom_style, units)
        
        content += dump_table(system, prop_info=prop_info, float_format=float_format)
    
    returns = []
    
    # Save to the file-like object
    if hasattr(f, 'write'):
        f.write(content)
    
    # Save to the file name
    elif f is not None:
        with open(f, 'w') as fp:
            fp.write(content)
    
    # Return as a string
    else:
        returns.append(content)
    
    # Generate LAMMPS input lines
    if return_info is True:
        read_info = info_content(system, f, atom_style=atom_style, units=units,
                                 potential=potential,
                                 return_pair_info=return_pair_info)
        returns.append(read_info)
    elif return_pair_info is True:
        raise ValueError('return_pair_info = True requires that return_info = True')
    
    if len(returns) == 1:
        return returns[0]
    
    elif len(returns) > 1:
        return tuple(returns)

def box_content(system, units, float_format):
    """
    Generates the data file lines associated with box dimensions.

    Parameters
    ----------
    system : atomman.System
    units : str
    float_format : str
    """

    # Get unit information according to the units style
    units_dict = style.unit(units)
    length_unit = units_dict['length']

    # Define line format strings
    xf2 = float_format + ' ' + float_format
    xf3 = float_format + ' ' + float_format + ' ' + float_format

    # Extract and convert box values
    xlo = uc.get_in_units(system.box.xlo, length_unit)
    xhi = uc.get_in_units(system.box.xhi, length_unit)
    ylo = uc.get_in_units(system.box.ylo, length_unit)
    yhi = uc.get_in_units(system.box.yhi, length_unit)
    zlo = uc.get_in_units(system.box.zlo, length_unit)
    zhi = uc.get_in_units(system.box.zhi, length_unit)
    xy = uc.get_in_units(system.box.xy, length_unit)
    xz = uc.get_in_units(system.box.xz, length_unit)
    yz = uc.get_in_units(system.box.yz, length_unit)
    
    # Write box values
    content = ''
    content += xf2 % (xlo, xhi) +' xlo xhi\n'
    content += xf2 % (ylo, yhi) +' ylo yhi\n'
    content += xf2 % (zlo, zhi) +' zlo zhi\n'
    if xy != 0.0 or xz != 0.0 or yz != 0.0:
        content += xf3 % (xy, xz, yz) + ' xy xz yz\n'

    return content

def atoms_content(system, imageflags, atom_style, units, float_format):
    
    content = ''
    content += f'\nAtoms # {atom_style}\n\n'
    prop_info = atoms_prop_info(atom_style, units)

    # Check if imageflags are needed
    if np.allclose(imageflags, 0):
        extra = None
    else:
        extra = OrderedDict()
        extra['imageflag_a'] = imageflags[:,0]
        extra['imageflag_b'] = imageflags[:,1]
        extra['imageflag_c'] = imageflags[:,2]
    
    content += dump_table(system, prop_info=prop_info, float_format=float_format, extra=extra)

    return content

def velocities_content(system, atom_style, units, float_format):
    
    content = ''

    if 'velocity' in system.atoms_prop():
        content += '\nVelocities\n\n'
        prop_info = velocities_prop_info(atom_style, units)
        
        content += dump_table(system, prop_info=prop_info, float_format=float_format)

    return content

def info_content(system, f, atom_style=None, units=None, potential=None,
                 return_pair_info=False):
    """
    Return appropriate units, atom_style, boundary, and read_data LAMMPS commands
    """
    if potential is not None and potential.pair_style == 'kim' and return_pair_info is True:
        return kim_info_content(system, f, potential)

    # Add comment line
    info = '# Script and atom data file prepared using atomman Python package\n\n'

    # Add units and atom_style values
    info += f'units {units}\n'
    info += f'atom_style {atom_style}\n\n'

    # Set boundary flags to p or m based on pbc values
    bflags = np.array(['m','m','m'])
    bflags[system.pbc] = 'p'
    info += f'boundary {bflags[0]} {bflags[1]} {bflags[2]}\n'
    
    # Set read_data command 
    if isinstance(f, str):
        info += f'read_data {f}\n'

    # Set pair_info
    if return_pair_info is True:
        if potential is None:
            raise ValueError('return_pair_info = True requires that potential be given')
        
        info += '\n'
        info += potential.pair_info(symbols=system.symbols,
                                    masses=system.masses)

    return info

def kim_info_content(system, f, potential):
    """
    Return appropriate units, atom_style, boundary, and read_data LAMMPS commands
    """
    # Add comment line
    info = '# Script and atom data file prepared using atomman Python package\n\n'

    # Generate pair_info
    pair_info_lines = potential.pair_info(symbols=system.symbols,
                                          masses=system.masses).split('\n')
    
    # Add kim init
    info += pair_info_lines[0] + '\n'

    # Set boundary flags to p or m based on pbc values
    bflags = np.array(['m','m','m'])
    bflags[system.pbc] = 'p'
    info += f'boundary {bflags[0]} {bflags[1]} {bflags[2]}\n'
    
    # Set read_data command 
    if isinstance(f, str):
        info += f'read_data {f}\n'

    # Add remaining pair info lines
    info += '\n'.join(pair_info_lines[1:]) + '\n'

    return info

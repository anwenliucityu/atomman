import numpy as np

from . import free_surface_basis
from ..tools.crystalsystem import iscubic
from ..tools import miller

class FreeSurface():
    """
    Class for generating free surface atomic configurations using clean planar slices. 
    """
    
    def __init__(self, hkl, ucell, cutboxvector='c', maxindex=None,
                 conventional_setting='p', tol=1e-7):
        """
        Class initializer.  Identifies the proper rotations for the given hkl plane
        and cutboxvector, and creates the rotated cell.
        
        Parameters
        ----------
        hkl : array-like object
            The free surface plane to generate expressed in either 3 indices
            Miller (hkl) format or 4 indices Miller-Bravais (hkil) format.
        ucell : atomman.System
            The unit cell to use in generating the system.
        cutboxvector : str, optional
            Specifies which of the three box vectors corresponds to the
            out-of-plane vector.  Default value is c.
        maxindex : int, optional
            Max uvw index value to use in identifying the best uvw set for the
            out-of-plane vector.  If not given, will use the largest absolute
            index between the given hkl and the initial in-plane vector guesses.
        conventional_setting : str, optional
            Allows for rotations of a primitive unit cell to be determined from
            (hkl) indices specified relative to a conventional unit cell.  Allowed
            settings: 'p' for primitive (no conversion), 'f' for face-centered,
            'i' for body-centered, and 'a', 'b', or 'c' for side-centered.  Default
            behavior is to perform no conversion, i.e. take (hkl) relative to the
            given ucell.
        tol : float, optional
            Tolerance parameter used to round off near-zero values.  Default
            value is 1e-8.
        """
        
        # Pass parameters to free_surface_basis to get the rotation uvws
        uvws = free_surface_basis(hkl, box=ucell.box, cutboxvector=cutboxvector, maxindex=maxindex,
                                  conventional_setting=conventional_setting)
        
        # Generate the rotated cell
        rcell, transform = ucell.rotate(uvws, return_transform=True)
        
        # Transform uvws to the conventional cell representation
        if uvws.shape == (3,3):
            uvws = miller.vector_primitive_to_conventional(uvws, conventional_setting)

        # Set cutindex and rcellwidth based on cutboxvector
        if cutboxvector == 'a':
            if rcell.box.bvect[0] != 0.0 or rcell.box.cvect[0] != 0.0:
                raise ValueError("box bvect and cvect cannot have x component for cutboxvector='a'")
            cutindex = 0
        
        elif cutboxvector == 'b':
            if rcell.box.avect[1] != 0.0 or rcell.box.cvect[1] != 0.0:
                raise ValueError("box avect and cvect cannot have y component for cutboxvector='b'")
            cutindex = 1

        elif cutboxvector == 'c':
            if rcell.box.avect[2] != 0.0 or rcell.box.bvect[2] != 0.0:
                raise ValueError("box avect and bvect cannot have z component for cutboxvector='c'")
            cutindex = 2
        
        # Define out of plane unit vector 
        ovect = np.zeros(3)
        ovect[cutindex] = 1.0
        
        # Get out of plane width
        rcellwidth = rcell.box.vects[cutindex, cutindex]
        
        # Get the unique coordinates normal to the plane
        pos = rcell.atoms.pos
        numdec = - int(np.floor(np.log10(tol)))
        coords = np.unique(pos[:, cutindex].round(numdec))

        # Add periodic replica if missing
        if not np.isclose(coords[-1] - coords[0], rcellwidth, rtol=0.0, atol=tol):
            coords = np.append(coords, coords[0] + rcellwidth)
            
        # Compute the shifts
        relshifts = rcellwidth - (coords[1:] + coords[:-1]) / 2
        relshifts[relshifts > rcellwidth] -= rcellwidth
        relshifts[relshifts < 0.0] += rcellwidth
        shifts = np.outer(np.sort(relshifts), ovect)
        
        # Save attributes
        self.__hkl = np.asarray(hkl)
        self.__ucell = ucell
        self.__rcell = rcell
        self.__cutboxvector = cutboxvector
        self.__cutindex = cutindex
        self.__uvws = uvws
        self.__rcellwidth = rcellwidth
        self.__shifts = shifts
        self.__transform = transform
        self.__conventional_setting = conventional_setting

    @property
    def hkl(self):
        """list : Crystal plane in Miller or Miller-Bravais indices"""
        return self.__hkl
    
    @property
    def ucell(self):
        """atomman.System : The unit cell to use in building the defect system."""
        return self.__ucell
    
    @property
    def rcell(self):
        """atomman.System : the rotated cell to use in building the defect system."""
        return self.__rcell
    
    @property
    def cutboxvector(self):
        """str : The box vector for the cut direction."""
        return self.__cutboxvector
    
    @property
    def cutindex(self):
        """int : The Cartesian index for the cut direction."""
        return self.__cutindex
    
    @property
    def uvws(self):
        """numpy.ndarray : The conventional Miller or Miller-Bravais crystal vectors associated with the rcell box vectors."""
        return self.__uvws
    
    @property
    def rcellwidth(self):
        """float : The width of rcell in the cutindex direction."""
        return self.__rcellwidth
    
    @property
    def shifts(self):
        """list : All shift values that place the fault halfway between atomic layers in rcell."""
        return self.__shifts
    
    @property
    def system(self):
        """atomman.System : The built free surface system."""
        try:
            return self.__system
        except:
            raise AttributeError('system not yet built. Use build_system() or surface().')
        
    @property
    def surfacearea(self):
        """float : The surface area of one of the hkl planes."""
        try:
            return self.__surfacearea
        except:
            raise AttributeError('system not yet built. Use build_system() or surface().')
        
    @property
    def transform(self):
        """numpy.ndarray : The Cartesian transformation tensor associated with rotating from ucell to rcell"""
        return self.__transform
    
    @property
    def conventional_setting(self):
        """str : The lattice setting/centering associated with the conventional cell (used if ucell is primitive)"""
        return self.__conventional_setting

    def surface(self, shift=None, vacuumwidth=None, minwidth=None, sizemults=None,
                even=False):
        """
        Generates and returns a free surface atomic system.
        
        Parameters
        ----------
        shift : array-like object, optional
            Applies a shift to all atoms. Different values allow for free surfaces with
            different termination planes to be selected.
        vacuumwidth : float, optional
            If given, the free surface is created by modifying the system's box to insert
            a region of vacuum with this width. This is typically used for DFT calculations
            where it is computationally preferable to insert a vacuum region and keep all
            dimensions periodic.
        sizemults : list or tuple, optional
            The three System.supersize multipliers [a_mult, b_mult, c_mult] to use on the
            rotated cell to build the final system. Note that the cutboxvector sizemult
            must be an integer and not a tuple.  Default value is [1, 1, 1].
        minwidth : float, optional
            If given, the sizemult along the cutboxvector will be selected such that the
            width of the resulting final system in that direction will be at least this
            value. If both sizemults and minwidth are given, then the larger of the two
            in the cutboxvector direction will be used. 
        even : bool, optional
            A True value means that the sizemult for cutboxvector will be made an even
            number by adding 1 if it is odd.  Default value is False.       

        Returns
        -------
        atomman.System
            The free surface atomic system.
        """

        # Set default function values
        if shift is None:
            shift = np.zeros(3)
        else:
            shift = np.asarray(shift)
        
        if sizemults is None:
            sizemults = [1, 1, 1]
        
        # Handle minwidth
        if minwidth is not None:
            mult = int(np.ceil(minwidth / self.rcellwidth))
            
            sizemult = sizemults[self.cutindex]
            if mult > np.abs(sizemult):
                sizemults[self.cutindex] = np.sign(sizemult) * mult
        
        # Handle even
        if even and sizemults[self.cutindex] % 2 == 1:
            if sizemults[self.cutindex] > 0:
                sizemults[self.cutindex] += 1
            else:
                sizemults[self.cutindex] -= 1
        
        # Define out of plane unit vector 
        ovect = np.zeros(3)
        ovect[self.cutindex] = 1.0

        # Supersize and shift the system
        system = self.rcell.supersize(*sizemults)
        system.atoms.pos += shift
        system.wrap()
        
        # Change system's pbc
        system.pbc = [True, True, True]
        system.pbc[self.cutindex] = False
        
        # Insert vacuumwidth
        if vacuumwidth is not None:
            if vacuumwidth < 0:
                raise ValueError('vacuumwidth must be positive')
            newvects = system.box.vects
            newvects[self.cutindex, self.cutindex] += vacuumwidth
            neworigin = system.box.origin - ovect * vacuumwidth / 2 
            system.box_set(vects=newvects, origin=neworigin)
               
        # Compute surfacearea based on cutboxvector
        if self.cutboxvector == 'a':
            surfacearea = np.linalg.norm(np.cross(system.box.bvect, system.box.cvect))

        elif self.cutboxvector == 'b':
            surfacearea = np.linalg.norm(np.cross(system.box.avect, system.box.cvect))

        elif self.cutboxvector == 'c':
            surfacearea = np.linalg.norm(np.cross(system.box.avect, system.box.bvect))
                        
        # Save attributes
        self.__system = system
        self.__surfacearea = surfacearea

        return self.system
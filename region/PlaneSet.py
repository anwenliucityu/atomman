# coding: utf-8

# http://www.numpy.org/
import numpy as np

from . import Shape, Plane

class PlaneSet(Shape):
    """
    Class consisting of a shape defined by a set of planes
    """
    def __init__(self, planes):
        """
        Defines a shape based on a list of Plane objects
        
        Parameters
        ----------
        planes : list of atomman.region.Plane
            The planes to use in constructing the shape.  Points "below" all
            planes are considered inside the shape.
        """
        self.planes = planes
    
    @property 
    def planes(self):
        """list of atomman.region.Plane : The planes that make up the shape"""
        return self.__planes
    
    @planes.setter
    def planes(self, value):
        if isinstance(value, Plane):
            value = [value]
        else:
            value = list(value)
            for v in value:
                assert isinstance(v, Plane)
        self.__planes = value

    def inside(self, pos, inclusive=True):
        """
        Indicates if position(s) are inside the shape.
        
        Parameters
        ----------
        pos : array-like object
            Nx3 array of coordinates. 
        inclusive : bool, optional
            Indicates if points on the shape's boundaries are to be included.
            Default value is True.
        
        Returns
        -------
        numpy.NDArray
            N array of bool values: True if inside shape
        """
        
        # Ensure pos is a numpy array 
        pos = np.asarray(pos)
        
        # Construct test array with all Trues
        insideplanes = np.ones(len(pos), dtype=bool)
        
        # Loop over each plane and check if pos are below
        for plane in self.planes:
            insideplanes = insideplanes & plane.below(pos, inclusive=inclusive)
        
        return insideplanes
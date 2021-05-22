# coding: utf-8

class Shape():
    """
    Template class for defining geometric regions in space.
    """

    def __init__(self):
        """
        Defines a shape
        """
        raise NotImplementedError('Base shape class cannot be directly used')
        
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
        raise NotImplementedError('Base shape class cannot be directly used')
        
    def outside(self, pos, inclusive=False):
        """
        Indicates if position(s) are inside the shape.
        
        Parameters
        ----------
        pos : array-like object
            Nx3 array of coordinates. 
        inclusive : bool, optional
            Indicates if points on the shape's boundaries are to be included.
            Default value is False.
        
        Returns
        -------
        numpy.NDArray
            N array of bool values: True if outside shape
        """
        return ~self.inside(pos, inclusive=not inclusive)
        
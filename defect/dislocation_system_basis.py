from .. import Box, System
from ..tools import vect_angle, miller
from . import dislocation_system_transform

import numpy as np

def dislocation_system_basis(ξ_uvw, slip_hkl, m=None, n=None, box=None, tol=1e-8, maxindex=10,
                             return_hexagonal=False, return_transform=False):
    
    # Set default box to be cubic
    if box is None:
        box = Box()

    # Handle inputs 
    if m is None:
        m = np.array([1,0,0], dtype=float)
    m = np.asarray(m, dtype=float)
    if n is None:
        n = np.array([0,1,0], dtype=float)
    n = np.asarray(n, dtype=float)
    
    # Change ξ_uvw from uvtw if needed
    ξ_uvw = np.asarray(ξ_uvw, dtype=float)
    if ξ_uvw.shape == (4, ):
        ξ_uvw = miller.vector4to3(ξ_uvw)

    # Change slip_hkl from hkil if needed
    slip_hkl = np.asarray(slip_hkl, dtype=float)
    if slip_hkl.shape == (4, ):
        slip_hkl = miller.plane4to3(slip_hkl)

    # Get the transformation matrix for the system
    transform = dislocation_system_transform(ξ_uvw, slip_hkl, m=m, n=n, box=box, tol=1e-8)
    
    # Get orientation settings
    if np.isclose(np.abs(m[0]), 1.0, atol=tol):
        m_cart = transform[0]
    elif np.isclose(np.abs(m[1]), 1.0, atol=tol):
        m_cart = transform[1]
    elif np.isclose(np.abs(m[2]), 1.0, atol=tol):
        m_cart = transform[2]
    else:
        raise ValueError('m must be parallel to a Cartesian axis for this method')
    
    if np.isclose(np.abs(n[0]), 1.0, atol=tol):
        cutboxvector = 'a'
        n_cart = transform[0]
    elif np.isclose(np.abs(n[1]), 1.0, atol=tol):
        cutboxvector = 'b'
        n_cart = transform[1]
    elif np.isclose(np.abs(n[2]), 1.0, atol=tol):
        cutboxvector = 'c'
        n_cart = transform[2]
    else:
        raise ValueError('n must be parallel to a Cartesian axis for this method')
    
    ξ = np.cross(m, n)
    if np.isclose(np.abs(ξ[0]), 1.0, atol=tol):
        ξboxvector = 'a'
    elif np.isclose(np.abs(ξ[1]), 1.0, atol=tol):
        ξboxvector = 'b'
    elif np.isclose(np.abs(ξ[2]), 1.0, atol=tol):
        ξboxvector = 'c'
    else:
        raise ValueError('ξ must be parallel to a Cartesian axis for this method')
    
    # Build gen_vector iterator for testing vectors
    def gen_vector(n):
        for kk in range(0, n+1):
            for sk in [1, -1]:
                k = sk * kk
                for jj in range(0, n+1):
                    for sj in [1, -1]:
                        j = sj * jj
                        for ii in range(0, n+1):
                            for si in [1, -1]:
                                i = si * ii
                                if i==0 and j==0 and k==0:
                                    continue
                                yield np.array([i, j, k], dtype=int)
                                
    # Identify the two crystal vectors that best correspond to m_cart and n_cart
    m_uvw = None
    n_uvw = None    
    m_angle_min = 180
    n_angle_min = 180
    
    for uvw in gen_vector(maxindex):
        cart = np.inner(uvw, box.vects.T)
        m_angle = vect_angle(cart, m_cart)
        n_angle = vect_angle(cart, n_cart)
        
        # Find in-plane vector closest to m
        if np.isclose(np.dot(cart, n_cart), 0.0) and m_angle < m_angle_min:
            m_uvw = uvw
            m_angle_min = m_angle
        
        # Find vector closest to n
        elif n_angle < n_angle_min:
            n_angle_min = n_angle
            n_uvw = uvw
    
    assert m_uvw is not None, 'Failed to find vector near edge component direction'
    assert n_uvw is not None, 'Failed to find vector near slip plane normal'
    
    # Reduce m_uvw and n_uvw if possible
    m_uvw = m_uvw / np.gcd.reduce(np.asarray(m_uvw, dtype=int)) # pylint: disable=no-member
    n_uvw = n_uvw / np.gcd.reduce(np.asarray(n_uvw, dtype=int)) # pylint: disable=no-member
    
    # Orient the uvw sets based on cutboxvector and ξboxvector
    if cutboxvector == 'c':
        if ξboxvector == 'a':
            uvws = np.array([ξ_uvw, m_uvw, n_uvw])
        elif ξboxvector == 'b':
            uvws = np.array([-m_uvw, ξ_uvw, n_uvw])
        else:
            raise RuntimeError('Encountered cutboxvector == ξboxvector: should not be possible!')
    elif cutboxvector == 'b':
        if ξboxvector == 'c':
            uvws = np.array([m_uvw, n_uvw, ξ_uvw])
        elif ξboxvector == 'a':
            uvws = np.array([ξ_uvw, n_uvw, -m_uvw])
        else:
            raise RuntimeError('Encountered cutboxvector == ξboxvector: should not be possible!')
    elif cutboxvector == 'a':
        if ξboxvector == 'b':
            uvws = np.array([n_uvw, ξ_uvw, m_uvw])
        elif ξboxvector == 'c':
            uvws = np.array([n_uvw, -m_uvw, ξ_uvw])
        else:
            raise RuntimeError('Encountered cutboxvector == ξboxvector: should not be possible!')

    # Test if transform from rotation is consistent with transform from above
    system = System(box=box)
    system, test_transform = system.rotate(uvws, return_transform=True)
    
    assert np.allclose(transform, test_transform), 'Crystal system of box does not support the chosen m, n orientation'
    
    if return_hexagonal:
        uvws = miller.vector3to4(uvws)
    
    if return_transform:
    
        return uvws, transform
    else:
        return uvws